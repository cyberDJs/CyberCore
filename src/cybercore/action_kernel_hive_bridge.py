"""Local-only CyberHIVE dry-run bridge for the governed Action Kernel.

The caller supplies a trusted, preconfigured local registry. This module never
opens a network connection, enrolls nodes, or authorizes live actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
from threading import Lock
from typing import Any, Protocol

from cybercore.action_kernel import ExecutionReceipt, TaskRequest
from cybercore.action_kernel_interop import to_hive_health_dry_run


class ReplayGuard(Protocol):
    """Atomic claim store; production callers must use durable shared storage."""

    def claim_once(self, key: str) -> bool: ...


class InMemoryReplayGuard:
    """Thread-safe single-process guard for tests/local dry-run only."""

    def __init__(self) -> None:
        self._claimed: set[str] = set()
        self._lock = Lock()

    def claim_once(self, key: str) -> bool:
        with self._lock:
            if key in self._claimed:
                return False
            self._claimed.add(key)
            return True


@dataclass(frozen=True)
class HiveDryRunReceipt:
    request_id: str
    correlation_id: str
    target_id: str
    status: str
    reason: str


def run_local_hive_dry_run(
    task: TaskRequest,
    *,
    trusted_actor: str,
    kernel_receipt: ExecutionReceipt,
    registry: Any,
    replay_guard: ReplayGuard | None = None,
) -> HiveDryRunReceipt:
    """Require successful policy evaluation before constructing a typed Hive request.

    `registry` must be a trusted, in-process CyberHIVE NodeAgentRegistry.
    No arbitrary method/command routing is exposed to model input.
    """
    if kernel_receipt.status != "EXECUTED" or kernel_receipt.policy.decision != "ALLOW":
        raise PermissionError("Action Kernel policy did not allow task")
    if (
        kernel_receipt.task_id != task.task_id
        or kernel_receipt.correlation_id != task.correlation_id
        or kernel_receipt.actor != trusted_actor
        or kernel_receipt.capability != task.capability
        or kernel_receipt.target_id != task.target_id
    ):
        raise PermissionError("Task and authorization receipt do not match")

    if task.expires_at.tzinfo is None or task.expires_at <= datetime.now(timezone.utc):
        raise PermissionError("Task authorization expired")
    if replay_guard is None:
        raise PermissionError("Atomic replay guard required")

    shaped = to_hive_health_dry_run(task, trusted_actor=trusted_actor)
    key = f"{trusted_actor}:{task.task_id}:{task.correlation_id}"
    try:
        claimed = replay_guard.claim_once(key)
    except Exception as exc:
        raise PermissionError("Replay guard unavailable") from exc
    if not claimed:
        raise PermissionError("Authorization already consumed")

    # Optional dependency: installed only in a composed CyberCore+CyberHIVE runtime.
    # Import failure fails closed; it is not silently simulated as successful execution.
    node_agent = import_module("cyberhive_core.node_agent")
    AgentActionRequest = node_agent.AgentActionRequest
    AgentActionType = node_agent.AgentActionType

    hive_request = AgentActionRequest(
        id=shaped["id"],
        target_node=shaped["target_node"],
        action=AgentActionType.HEALTH_CHECK,
        payload={},
        dry_run=True,
        approval_tokens=(),
        requested_by=trusted_actor,
        correlation_id=task.correlation_id,
        created_at=task.requested_at,
    )
    result = registry.dispatch(hive_request)
    if (
        result.request_id != task.task_id
        or result.target_node != task.target_id
        or result.action != AgentActionType.HEALTH_CHECK
        or result.status.value != "dry_run"
    ):
        raise RuntimeError("Unexpected or non-dry-run CyberHIVE result")
    return HiveDryRunReceipt(
        request_id=result.request_id,
        correlation_id=task.correlation_id,
        target_id=result.target_node,
        status="dry_run",
        reason="HIVE_DRY_RUN_ONLY",
    )
