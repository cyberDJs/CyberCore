from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from operations import resolve_operation  # type: ignore[import-not-found]
    from protocol import (  # type: ignore[import-not-found]
        MAX_REQUEST_BYTES,
        RequestValidationError,
        ServerReceipt,
        ServerRequest,
    )
else:
    from cybercore.execution.server.operations import resolve_operation
    from cybercore.execution.server.protocol import (
        MAX_REQUEST_BYTES,
        RequestValidationError,
        ServerReceipt,
        ServerRequest,
    )


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _timeout_bytes(value: str | bytes | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8", errors="replace")


def execute_request(
    request: ServerRequest,
    *,
    runner: RunCallable = subprocess.run,
) -> ServerReceipt:
    spec = resolve_operation(request)
    started_at = _utc_now()

    try:
        completed = runner(
            list(spec.argv),
            shell=False,
            check=False,
            capture_output=True,
            timeout=spec.timeout_seconds,
        )
        completed_at = _utc_now()
        stdout = completed.stdout or b""
        stderr = completed.stderr or b""
        exit_code = int(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        completed_at = _utc_now()
        stdout = _timeout_bytes(exc.stdout)
        stderr = _timeout_bytes(exc.stderr) + b"\ncybercore-exec operation timed out"
        exit_code = 124

    return ServerReceipt(
        operation_id=request.operation_id,
        operation=request.operation,
        target_id=request.target_id,
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        authorization_reference=request.authorization_reference,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=exit_code,
        stdout_sha256=_digest(stdout),
        stderr_sha256=_digest(stderr),
        status="EXECUTED" if exit_code == 0 else "FAILED",
        mutation_possible=spec.mutating,
    )


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "secret_values_recorded": False,
    }


def _load_request(raw: bytes) -> ServerRequest:
    if len(raw) > MAX_REQUEST_BYTES:
        raise RequestValidationError("request exceeds the maximum encoded size")
    try:
        value: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestValidationError("request is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RequestValidationError("request root must be an object")
    return ServerRequest.from_mapping(value)


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        request = _load_request(raw)
        payload = execute_request(request).as_dict()
        exit_code = 0 if payload["status"] == "EXECUTED" else 1
    except RequestValidationError as exc:
        payload = _blocked(str(exc))
        exit_code = 2
    except OSError:
        payload = _blocked("fixed operation executable is unavailable")
        exit_code = 126

    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
