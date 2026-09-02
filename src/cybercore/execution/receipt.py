from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from cybercore.execution.models import ExecutionReceipt, ExecutionStatus, GovernedAction


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_receipt(
    action: GovernedAction,
    *,
    transport_argv: tuple[str, ...],
    started_at: str,
    completed_at: str,
    exit_code: int,
    stdout: bytes,
    stderr: bytes,
    mutation_possible: bool,
) -> ExecutionReceipt:
    status = ExecutionStatus.EXECUTED if exit_code == 0 else ExecutionStatus.FAILED
    return ExecutionReceipt(
        operation_id=action.operation_id,
        operation=action.operation,
        target_id=action.target_id,
        plan_id=action.plan_id,
        plan_revision=action.plan_revision,
        authorization_reference=action.authorization_reference,
        transport_argv=transport_argv,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=exit_code,
        stdout_sha256=digest_bytes(stdout),
        stderr_sha256=digest_bytes(stderr),
        status=status,
        mutation_possible=mutation_possible,
        secret_values_recorded=False,
    )
