from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone

if __package__ in {None, ""}:
    from authorization import (  # type: ignore[import-not-found]
        DenyAllExecutionAuthorizationVerifier,
        ExecutionAuthorizationVerifier,
    )
    from dispatcher import _blocked, _load_request  # type: ignore[import-not-found]
    from nextcloud_operations import (  # type: ignore[import-not-found]
        NEXTCLOUD_R1_TARGET_ID,
        resolve_nextcloud_r1_operation,
    )
    from protocol import (  # type: ignore[import-not-found]
        MAX_REQUEST_BYTES,
        RequestValidationError,
        ServerRequest,
    )
else:
    from cybercore.execution.authorization import (
        DenyAllExecutionAuthorizationVerifier,
        ExecutionAuthorizationVerifier,
    )
    from cybercore.execution.server.dispatcher import _blocked, _load_request
    from cybercore.execution.server.nextcloud_operations import (
        NEXTCLOUD_R1_TARGET_ID,
        resolve_nextcloud_r1_operation,
    )
    from cybercore.execution.server.protocol import (
        MAX_REQUEST_BYTES,
        RequestValidationError,
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


def _public_operation(value: str) -> str:
    if value == "nextcloud.r1.offhost.transfer":
        return "nextcloud.r1.offhost.transfer"
    if value == "nextcloud.r1.offhost.rollback":
        return "nextcloud.r1.offhost.rollback"
    raise RequestValidationError("unexpected operation after governed dispatch")


def execute_nextcloud_request(
    request: ServerRequest,
    *,
    authorization_verifier: ExecutionAuthorizationVerifier | None = None,
    runner: RunCallable = subprocess.run,
) -> dict[str, object]:
    spec = resolve_nextcloud_r1_operation(request)
    verifier = authorization_verifier or DenyAllExecutionAuthorizationVerifier()
    authorization = verifier.verify(
        operation_id=request.operation_id,
        operation=request.operation,
        target_id=request.target_id,
        plan_id=request.plan_id,
        plan_revision=request.plan_revision,
        authorization_reference=request.authorization_reference,
    )
    if not authorization.authorized:
        raise RequestValidationError("mutating request lacks verified authorization")

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

    return {
        "operation": _public_operation(spec.name),
        "target_id": NEXTCLOUD_R1_TARGET_ID,
        "request_schema_verified": True,
        "plan_binding_verified": True,
        "authorization_verified": True,
        "started_at": started_at,
        "completed_at": completed_at,
        "exit_code": exit_code,
        "stdout_sha256": _digest(stdout),
        "stderr_sha256": _digest(stderr),
        "status": "EXECUTED" if exit_code == 0 else "FAILED",
        "mutation_possible": True,
        "secret_values_recorded": False,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        request = _load_request(raw, expected_target_id=NEXTCLOUD_R1_TARGET_ID)
        payload = execute_nextcloud_request(request)
        exit_code = 0 if payload["status"] == "EXECUTED" else 1
    except RequestValidationError:
        payload = _blocked("request validation failed")
        exit_code = 2
    except OSError:
        payload = _blocked("fixed Nextcloud R1 operation executable is unavailable")
        exit_code = 126

    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
