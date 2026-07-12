import subprocess
from time import monotonic

from app.core.logging import mask_secret
from app.drivers.database.base import CommandResult, elapsed_since, tail_text


def run_command(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    input_file=None,
    output_file=None,
    timeout_seconds: int = 21600,
    output_limit: int = 8000,
) -> CommandResult:
    start = monotonic()
    try:
        completed = subprocess.run(
            args,
            env=env,
            stdin=input_file,
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
            stderr_tail=f"Command not found: {args[0]}",
            duration_seconds=elapsed_since(start),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            returncode=124,
            stdout_tail=tail_text(exc.stdout or b"", output_limit),
            stderr_tail=mask_secret(tail_text(exc.stderr or b"Timeout", output_limit)) or "",
            duration_seconds=elapsed_since(start),
        )

    stdout_tail = "" if output_file is not None else tail_text(completed.stdout or b"", output_limit)
    return CommandResult(
        ok=completed.returncode == 0,
        returncode=completed.returncode,
        stdout_tail=mask_secret(stdout_tail) or "",
        stderr_tail=mask_secret(tail_text(completed.stderr or b"", output_limit)) or "",
        duration_seconds=elapsed_since(start),
    )
