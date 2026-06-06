import os
import subprocess
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.errors import AppError
from app.schemas.kubeconfig import KubeconfigCreate, KubeconfigRead, KubeconfigTestResult

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


@router.get("", response_model=list[KubeconfigRead])
def list_kubeconfigs(
    _: dict = Depends(require_permission("database:read")),
):
    _ensure_kubeconfig_dir()
    files = sorted(KUBECONFIG_DIR.glob("*.yaml")) + sorted(KUBECONFIG_DIR.glob("*.yml"))
    results = []
    seen = set()
    for f in files:
        if f.stem in seen:
            continue
        seen.add(f.stem)
        results.append(KubeconfigRead(**_parse_kubeconfig(f)))
    return results


@router.post("", response_model=KubeconfigRead)
def create_kubeconfig(
    payload: KubeconfigCreate,
    _: dict = Depends(require_permission("database:write")),
):
    _ensure_kubeconfig_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in payload.name)
    if not safe_name:
        raise AppError("INVALID_INPUT", "Invalid kubeconfig name", status_code=400)
    try:
        yaml.safe_load(payload.content)
    except yaml.YAMLError as e:
        raise AppError("INVALID_INPUT", f"Invalid YAML content: {e}", status_code=400) from e
    target = KUBECONFIG_DIR / f"{safe_name}.yaml"
    if target.exists():
        raise AppError("ALREADY_EXISTS", f"Kubeconfig '{safe_name}' already exists", status_code=409)
    target.write_text(payload.content, encoding="utf-8")
    return KubeconfigRead(**_parse_kubeconfig(target))


@router.delete("/{name}")
def delete_kubeconfig(
    name: str,
    _: dict = Depends(require_permission("database:write")),
):
    _ensure_kubeconfig_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    for ext in (".yaml", ".yml"):
        target = KUBECONFIG_DIR / f"{safe_name}{ext}"
        if target.exists():
            target.unlink()
            return {"message": "deleted"}
    raise AppError("RESOURCE_NOT_FOUND", f"Kubeconfig '{name}' not found", status_code=404)


@router.post("/{name}/test", response_model=KubeconfigTestResult)
def test_kubeconfig(
    name: str,
    context: str | None = None,
    _: dict = Depends(require_permission("database:read")),
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

    args = ["kubectl", "--kubeconfig", str(target)]
    if context:
        args.extend(["--context", context])
    args.extend(["auth", "can-i", "get", "pods", "--all-namespaces"])

    try:
        result = subprocess.run(args, capture_output=True, timeout=15, check=False)
        allowed = result.stdout.decode("utf-8", errors="replace").strip().lower() == "yes"
    except subprocess.TimeoutExpired:
        return KubeconfigTestResult(ok=False, message="Connection timed out", namespaces=None)
    except FileNotFoundError:
        return KubeconfigTestResult(ok=False, message="kubectl not found", namespaces=None)

    if not allowed:
        msg = result.stderr.decode("utf-8", errors="replace").strip()
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

    return KubeconfigTestResult(ok=True, message=None, namespaces=namespaces)
