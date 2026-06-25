import json
import subprocess
from dataclasses import dataclass
from time import monotonic

from app.drivers.database.base import CommandResult, elapsed_since, tail_text


@dataclass
class K8sConfig:
    namespace: str = "default"
    pod_name: str | None = None
    label_selector: str | None = None
    container: str | None = None
    kubeconfig: str | None = None
    context: str | None = None

    @classmethod
    def from_dict(cls, data: dict | None) -> "K8sConfig":
        if not data:
            return cls()
        return cls(
            namespace=data.get("namespace", "default"),
            pod_name=data.get("pod_name") or None,
            label_selector=data.get("label_selector") or None,
            container=data.get("container") or None,
            kubeconfig=data.get("kubeconfig") or None,
            context=data.get("context") or None,
        )


def _build_kubectl_base_args(config: K8sConfig) -> list[str]:
    args = ["kubectl"]
    if config.kubeconfig:
        args.extend(["--kubeconfig", config.kubeconfig])
    if config.context:
        args.extend(["--context", config.context])
    if config.namespace:
        args.extend(["-n", config.namespace])
    return args


def build_kubectl_exec_args(config: K8sConfig, command: list[str], env_vars: dict[str, str] | None = None) -> list[str]:
    args = _build_kubectl_base_args(config)
    args.append("exec")
    if config.pod_name:
        args.append(config.pod_name)
    elif config.label_selector:
        args.extend(["-l", config.label_selector])
    if config.container:
        args.extend(["-c", config.container])
    args.append("--stdin")
    args.append("--")
    if env_vars:
        args.append("env")
        for key, value in env_vars.items():
            args.append(f"{key}={value}")
    args.extend(command)
    return args


def resolve_pod_name(config: K8sConfig, timeout_seconds: int = 10) -> str | None:
    if config.pod_name:
        return config.pod_name
    if not config.label_selector:
        return None
    args = _build_kubectl_base_args(config)
    args.extend([
        "get", "pods",
        "-l", config.label_selector,
        "-o", "jsonpath={.items[0].metadata.name}",
    ])
    try:
        result = subprocess.run(
            args, capture_output=True, timeout=timeout_seconds, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.decode("utf-8", errors="replace").strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def run_kubectl_command(
    config: K8sConfig,
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    input_file=None,
    output_file=None,
    timeout_seconds: int = 21600,
) -> CommandResult:
    k8s_env_vars = {}
    if env:
        for key in ["MYSQL_PWD", "PGPASSWORD"]:
            if key in env:
                k8s_env_vars[key] = env[key]
    start = monotonic()
    pod_name = resolve_pod_name(config)
    if not pod_name:
        return CommandResult(
            ok=False,
            returncode=1,
            stdout_tail="",
            stderr_tail="Kubernetes pod not found. Provide pod_name or a label_selector that matches a pod.",
            duration_seconds=elapsed_since(start),
        )
    exec_config = K8sConfig(
        namespace=config.namespace,
        pod_name=pod_name,
        container=config.container,
        kubeconfig=config.kubeconfig,
        context=config.context,
    )
    args = build_kubectl_exec_args(exec_config, command, env_vars=k8s_env_vars if k8s_env_vars else None)
    try:
        completed = subprocess.run(
            args,
            env=env,
            stdin=input_file if input_file is not None else subprocess.PIPE,
            stdout=output_file if output_file is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        return CommandResult(
            ok=False,
            returncode=127,
            stdout_tail="",
            stderr_tail="kubectl command not found. Ensure kubectl is installed.",
            duration_seconds=elapsed_since(start),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            returncode=124,
            stdout_tail=tail_text(exc.stdout or b""),
            stderr_tail=tail_text(exc.stderr or b"Timeout"),
            duration_seconds=elapsed_since(start),
        )

    stdout_tail = "" if output_file is not None else tail_text(completed.stdout or b"")
    return CommandResult(
        ok=completed.returncode == 0,
        returncode=completed.returncode,
        stdout_tail=stdout_tail,
        stderr_tail=tail_text(completed.stderr or b""),
        duration_seconds=elapsed_since(start),
    )


def test_kubectl_access(config: K8sConfig, timeout_seconds: int = 15) -> dict:
    args = _build_kubectl_base_args(config)
    args.extend(["auth", "can-i", "exec", "pods"])
    try:
        result = subprocess.run(
            args, capture_output=True, timeout=timeout_seconds, check=False,
        )
        allowed = result.stdout.decode("utf-8", errors="replace").strip().lower() == "yes"
        return {
            "ok": allowed,
            "message": None if allowed else "kubectl does not have permission to exec into pods",
        }
    except FileNotFoundError:
        return {"ok": False, "message": "kubectl command not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "kubectl command timed out"}


def list_namespaces(kubeconfig: str | None = None, context: str | None = None, timeout_seconds: int = 10) -> list[str]:
    args = ["kubectl"]
    if kubeconfig:
        args.extend(["--kubeconfig", kubeconfig])
    if context:
        args.extend(["--context", context])
    args.extend(["get", "namespaces", "-o", "jsonpath={.items[*].metadata.name}"])
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout_seconds, check=False)
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace").strip().split()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return []


def list_pods(
    namespace: str,
    kubeconfig: str | None = None,
    context: str | None = None,
    timeout_seconds: int = 10,
) -> list[dict]:
    args = ["kubectl"]
    if kubeconfig:
        args.extend(["--kubeconfig", kubeconfig])
    if context:
        args.extend(["--context", context])
    if namespace:
        args.extend(["-n", namespace])
    args.extend(["get", "pods", "-o", "json"])
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout_seconds, check=False)
        if result.returncode == 0:
            data = json.loads(result.stdout.decode("utf-8", errors="replace"))
            pods = []
            for item in data.get("items", []):
                meta = item.get("metadata", {})
                spec = item.get("spec", {})
                containers = [c.get("name", "") for c in spec.get("containers", [])]
                pods.append({
                    "name": meta.get("name", ""),
                    "status": item.get("status", {}).get("phase", ""),
                    "containers": containers,
                })
            return pods
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return []
