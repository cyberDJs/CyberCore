from __future__ import annotations

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
from cybercore.execution.server.protocol import PROTOCOL_VERSION


class ExecutionBlockedError(RuntimeError):
    """Raised when the governed execution policy blocks an action."""


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]
TRANSPORT_TIMEOUT_SECONDS = 180


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
    return build_receipt(
        action,
        transport_argv=argv,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        mutation_possible=decision.mutating,
    )
