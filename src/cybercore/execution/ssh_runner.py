from __future__ import annotations

from datetime import datetime
import hashlib
import json
import subprocess
from typing import Callable

from cybercore.execution.authorization import (
    DenyAllExecutionAuthorizationVerifier,
    ExecutionAuthorizationVerifier,
)
from cybercore.execution.models import ExecutionReceipt, ExecutionTarget, GovernedAction
from cybercore.execution.policy import evaluate_action
from cybercore.execution.receipt import build_receipt, utc_now
from cybercore.execution.server.inventory import validate_inventory_payload
from cybercore.execution.server.protocol import PROTOCOL_VERSION


class ExecutionBlockedError(RuntimeError):
    """Raised when the governed execution policy blocks an action."""


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]
TRANSPORT_TIMEOUT_SECONDS = 180
_INVENTORY_RECEIPT_KEYS = frozenset(
    {
        "operation_id",
        "operation",
        "target_id",
        "plan_id",
        "plan_revision",
        "authorization_reference_sha256",
        "started_at",
        "completed_at",
        "exit_code",
        "stdout_sha256",
        "stderr_sha256",
        "status",
        "mutation_possible",
        "result",
        "secret_values_recorded",
    }
)
_SHA256_HEX_DIGITS = frozenset("0123456789abcdef")


def build_transport_argv(target: ExecutionTarget) -> tuple[str, ...]:
    return (
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=15",
        "-s",
        f"{target.ssh_user}@{target.hostname}",
        target.subsystem,
    )


def _request_bytes(action: GovernedAction) -> bytes:
    payload = {
        "version": PROTOCOL_VERSION,
        "operation_id": action.operation_id,
        "operation": action.operation,
        "target_id": action.target_id,
        "plan_id": action.plan_id,
        "plan_revision": action.plan_revision,
        "authorization_reference": action.authorization_reference,
        "arguments": dict(action.arguments),
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _timeout_bytes(value: str | bytes | None) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode()
    return b""


def _require_server_receipt_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _SHA256_HEX_DIGITS for character in value)
    ):
        raise ValueError(f"server response {label} is not a SHA-256 digest")
    return value


def _require_server_receipt_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"server response {label} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"server response {label} is not a timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"server response {label} must be timezone-aware")
    return parsed


def _inventory_result_from_server_response(
    action: GovernedAction,
    stdout: bytes,
) -> dict[str, object]:
    try:
        payload = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("server response is not valid inventory JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("server response is not an object")
    if frozenset(payload) != _INVENTORY_RECEIPT_KEYS:
        raise ValueError("server response fields do not match the exact receipt schema")

    exit_code = payload["exit_code"]
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
        raise ValueError("server response exit_code is inconsistent with successful inventory")

    started_at = _require_server_receipt_timestamp(payload["started_at"], "started_at")
    completed_at = _require_server_receipt_timestamp(payload["completed_at"], "completed_at")
    if completed_at < started_at:
        raise ValueError("server response completed_at precedes started_at")

    _require_server_receipt_sha256(payload["stdout_sha256"], "stdout_sha256")
    _require_server_receipt_sha256(payload["stderr_sha256"], "stderr_sha256")

    expected = {
        "operation_id": action.operation_id,
        "operation": action.operation,
        "target_id": action.target_id,
        "plan_id": action.plan_id,
        "plan_revision": action.plan_revision,
        "authorization_reference_sha256": hashlib.sha256(
            action.authorization_reference.encode("utf-8")
        ).hexdigest(),
        "status": "EXECUTED",
        "mutation_possible": False,
        "secret_values_recorded": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise ValueError(f"server response binding mismatch: {key}")
    return validate_inventory_payload(payload.get("result"))


def execute_action(
    action: GovernedAction,
    target: ExecutionTarget,
    *,
    authorization_verifier: ExecutionAuthorizationVerifier | None = None,
    run: RunCallable = subprocess.run,
) -> ExecutionReceipt:
    decision = evaluate_action(action, target)
    if not decision.allowed:
        raise ExecutionBlockedError(decision.reason)

    if decision.mutating:
        verifier = authorization_verifier or DenyAllExecutionAuthorizationVerifier()
        authorization = verifier.verify(
            operation_id=action.operation_id,
            operation=action.operation,
            target_id=action.target_id,
            plan_id=action.plan_id,
            plan_revision=action.plan_revision,
            authorization_reference=action.authorization_reference,
        )
        if not authorization.authorized:
            raise ExecutionBlockedError(authorization.reason)

    argv = build_transport_argv(target)
    started_at = utc_now()
    try:
        completed = run(
            list(argv),
            input=_request_bytes(action),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            timeout=TRANSPORT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        completed_at = utc_now()
        timeout_stderr = _timeout_bytes(exc.stderr) + b"\ncybercore-exec transport timed out"
        return build_receipt(
            action,
            transport_argv=argv,
            started_at=started_at,
            completed_at=completed_at,
            exit_code=124,
            stdout=_timeout_bytes(exc.stdout),
            stderr=timeout_stderr,
            mutation_possible=decision.mutating,
        )
    completed_at = utc_now()

    stdout = completed.stdout if isinstance(completed.stdout, bytes) else b""
    stderr = completed.stderr if isinstance(completed.stderr, bytes) else b""
    exit_code = int(completed.returncode)
    result = None
    if action.operation == "system.inventory" and exit_code == 0:
        try:
            result = _inventory_result_from_server_response(action, stdout)
        except ValueError:
            exit_code = 65
            stderr += b"\ncybercore-exec structured inventory response failed validation"

    return build_receipt(
        action,
        transport_argv=argv,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        mutation_possible=decision.mutating,
        result=result,
    )
