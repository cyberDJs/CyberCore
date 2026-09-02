from __future__ import annotations

import json
import subprocess
from typing import Callable

from cybercore.execution.models import ExecutionReceipt, ExecutionTarget, GovernedAction
from cybercore.execution.policy import evaluate_action
from cybercore.execution.receipt import build_receipt, utc_now


class ExecutionBlockedError(RuntimeError):
    """Raised when the governed execution policy blocks an action."""


RunCallable = Callable[..., subprocess.CompletedProcess[bytes]]


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
        "version": 1,
        "operation_id": action.operation_id,
        "operation": action.operation,
        "target_id": action.target_id,
        "plan_id": action.plan_id,
        "plan_revision": action.plan_revision,
        "authorization_reference": action.authorization_reference,
        "arguments": dict(action.arguments),
    }
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def execute_action(
    action: GovernedAction,
    target: ExecutionTarget,
    *,
    run: RunCallable = subprocess.run,
) -> ExecutionReceipt:
    decision = evaluate_action(action, target)
    if not decision.allowed:
        raise ExecutionBlockedError(decision.reason)

    argv = build_transport_argv(target)
    started_at = utc_now()
    completed = run(
        list(argv),
        input=_request_bytes(action),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=30,
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
