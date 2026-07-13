import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.database import get_db
from app.core.errors import AppError
from app.core.ownership import is_admin
from app.models import User
from app.schemas.kubeconfig import KubeconfigCreate, KubeconfigRead, KubeconfigTestResult
from app.services.audit_service import create_audit_log

router = APIRouter()

KUBECONFIG_DIR = Path(os.getenv("DBVAULT_KUBECONFIG_DIR", "/var/lib/dbvault/kubeconfigs"))


def _ensure_kubeconfig_dir():
    KUBECONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _parse_kubeconfig(path: Path) -> dict:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        contexts = []
        current_context = None
        if data and "contexts" in data:
            contexts = [ctx.get("name", "") for ctx in data["contexts"] if ctx.get("name")]
        if data and "current-context" in data:
            current_context = data["current-context"]
        created_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        return {
            "name": path.stem,
            "path": str(path),
            "contexts": contexts,
            "current_context": current_context,
            "created_at": created_at,
        }
    except Exception:
        return {
            "name": path.stem,
            "path": str(path),
            "contexts": [],
            "current_context": None,
            "created_at": "",
        }


def _metadata_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".meta.json")


def _read_owner(path: Path) -> int | None:
    metadata_path = _metadata_path(path)
    if not metadata_path.exists():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8")).get("created_by")
    except (json.JSONDecodeError, OSError):
        return None


def _write_owner(path: Path, user: User) -> None:
    _metadata_path(path).write_text(json.dumps({"created_by": user.id}), encoding="utf-8")


def _safe_load_kubeconfig(content: str) -> dict:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise AppError("INVALID_INPUT", f"Invalid YAML content: {e}", status_code=400) from e
    if not isinstance(data, dict):
        raise AppError("INVALID_INPUT", "Invalid kubeconfig content", status_code=400)
    for user_entry in data.get("users") or []:
        user_config = user_entry.get("user") if isinstance(user_entry, dict) else None
        if isinstance(user_config, dict) and "exec" in user_config:
            raise AppError("INVALID_INPUT", "Kubeconfig exec plugins are not allowed", status_code=400)
    return data


def _ensure_kubeconfig_owner(path: Path, user: User) -> None:
    if is_admin(user):
        return
    if _read_owner(path) != user.id:
        raise AppError("RESOURCE_NOT_FOUND", f"Kubeconfig '{path.stem}' not found", status_code=404)


@router.get("", response_model=list[KubeconfigRead])
def list_kubeconfigs(
    user: User = Depends(require_permission("database:read")),
):
    _ensure_kubeconfig_dir()
    files = sorted(KUBECONFIG_DIR.glob("*.yaml")) + sorted(KUBECONFIG_DIR.glob("*.yml"))
    results = []
    seen = set()
    for f in files:
        if f.stem in seen:
            continue
        if not is_admin(user) and _read_owner(f) != user.id:
            continue
        seen.add(f.stem)
        results.append(KubeconfigRead(**_parse_kubeconfig(f)))
    return results


@router.post("", response_model=KubeconfigRead)
def create_kubeconfig(
    payload: KubeconfigCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    _ensure_kubeconfig_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in payload.name)
    if not safe_name:
        raise AppError("INVALID_INPUT", "Invalid kubeconfig name", status_code=400)
    _safe_load_kubeconfig(payload.content)
    target = KUBECONFIG_DIR / f"{safe_name}.yaml"
    if target.exists():
        raise AppError("ALREADY_EXISTS", f"Kubeconfig '{safe_name}' already exists", status_code=409)
    target.write_text(payload.content, encoding="utf-8")
    _write_owner(target, user)
    create_audit_log(
        db,
        user=user,
        action="kubeconfig.create",
        resource_type="kubeconfig",
        resource_id=safe_name,
        request=request,
    )
    return KubeconfigRead(**_parse_kubeconfig(target))


@router.delete("/{name}")
def delete_kubeconfig(
    name: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:write")),
):
    _ensure_kubeconfig_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    for ext in (".yaml", ".yml"):
        target = KUBECONFIG_DIR / f"{safe_name}{ext}"
        if target.exists():
            _ensure_kubeconfig_owner(target, user)
            target.unlink()
            _metadata_path(target).unlink(missing_ok=True)
            create_audit_log(
                db,
                user=user,
                action="kubeconfig.delete",
                resource_type="kubeconfig",
                resource_id=safe_name,
                request=request,
            )
            return {"message": "deleted"}
    raise AppError("RESOURCE_NOT_FOUND", f"Kubeconfig '{name}' not found", status_code=404)


@router.post("/{name}/test", response_model=KubeconfigTestResult)
def test_kubeconfig(
    name: str,
    request: Request,
    context: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("database:read")),
):
    _ensure_kubeconfig_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    target = None
    for ext in (".yaml", ".yml"):
        candidate = KUBECONFIG_DIR / f"{safe_name}{ext}"
        if candidate.exists():
            target = candidate
            break
    if not target:
        raise AppError("RESOURCE_NOT_FOUND", f"Kubeconfig '{name}' not found", status_code=404)
    _ensure_kubeconfig_owner(target, user)

    args = ["kubectl", "--kubeconfig", str(target)]
    if context:
        args.extend(["--context", context])
    args.extend(["auth", "can-i", "get", "pods", "--all-namespaces"])

    try:
        result = subprocess.run(args, capture_output=True, timeout=15, check=False)
        allowed = result.stdout.decode("utf-8", errors="replace").strip().lower() == "yes"
    except subprocess.TimeoutExpired:
        create_audit_log(
            db,
            user=user,
            action="kubeconfig.test",
            resource_type="kubeconfig",
            resource_id=safe_name,
            request=request,
            result="failed",
            reason="Connection timed out",
        )
        return KubeconfigTestResult(ok=False, message="Connection timed out", namespaces=None)
    except FileNotFoundError:
        create_audit_log(
            db,
            user=user,
            action="kubeconfig.test",
            resource_type="kubeconfig",
            resource_id=safe_name,
            request=request,
            result="failed",
            reason="kubectl not found",
        )
        return KubeconfigTestResult(ok=False, message="kubectl not found", namespaces=None)

    if not allowed:
        msg = result.stderr.decode("utf-8", errors="replace").strip()
        create_audit_log(
            db,
            user=user,
            action="kubeconfig.test",
            resource_type="kubeconfig",
            resource_id=safe_name,
            request=request,
            result="failed",
            reason=msg or "permission denied",
        )
        return KubeconfigTestResult(ok=False, message=f"No permission: {msg}", namespaces=None)

    args_ns = ["kubectl", "--kubeconfig", str(target)]
    if context:
        args_ns.extend(["--context", context])
    args_ns.extend(["get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"])
    namespaces = []
    try:
        result = subprocess.run(args_ns, capture_output=True, timeout=10, check=False)
        if result.returncode == 0:
            namespaces = result.stdout.decode("utf-8", errors="replace").strip().split()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    create_audit_log(
        db,
        user=user,
        action="kubeconfig.test",
        resource_type="kubeconfig",
        resource_id=safe_name,
        request=request,
    )
    return KubeconfigTestResult(ok=True, message=None, namespaces=namespaces)
