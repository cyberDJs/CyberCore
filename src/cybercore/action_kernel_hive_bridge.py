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


# This process-local guard is owned by the bridge boundary and cannot be
# replaced per invocation. The caller-supplied ReplayGuard remains mandatory
# as the durable/shared claim layer for cooperating processes.
_PROCESS_REPLAY_GUARD = InMemoryReplayGuard()
_MISSING_CORRELATION = object()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_not_expired(task: TaskRequest) -> None:
    if task.expires_at.tzinfo is None or task.expires_at <= _utc_now():
        raise PermissionError("Task authorization expired")


def _claim_once(replay_guard: ReplayGuard, key: str) -> None:
    try:
        durable_claimed = replay_guard.claim_once(key)
    except Exception as exc:
        raise PermissionError("Replay guard unavailable") from exc
    if not durable_claimed:
        raise PermissionError("Authorization already consumed")

    if not _PROCESS_REPLAY_GUARD.claim_once(key):
        raise PermissionError("Authorization already consumed")


def run_local_hive_dry_run(
    task: TaskRequest,
    *,
    trusted_actor: str,
    kernel_receipt: ExecutionReceipt,
    registry: Any,
    replay_guard: ReplayGuard | None = None,
) -> HiveDryRunReceipt:
    """Require successful policy evaluation before a typed local Hive dry-run.

    `registry` must be a trusted, in-process CyberHIVE NodeAgentRegistry.
    `replay_guard` must be durable/shared for production use. A separate
    process-owned guard prevents per-call replacement from bypassing replay
    protection inside this bridge process.
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

    # Cheap early rejection before optional-runtime work.
    _assert_not_expired(task)
    if replay_guard is None:
        raise PermissionError("Atomic replay guard required")

    shaped = to_hive_health_dry_run(task, trusted_actor=trusted_actor)

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

    # Authorization lifetime is checked again immediately at the claim/dispatch
    # boundary so shaping/import/request construction cannot extend validity.
    _assert_not_expired(task)

    key = f"{trusted_actor}:{task.task_id}:{task.correlation_id}"
    _claim_once(replay_guard, key)

    # Durable claim acquisition may block long enough for the task to expire.
    # Claims remain consumed, but an expired task must never reach dispatch.
    _assert_not_expired(task)

    # Both claims intentionally remain consumed after this boundary, including
    # uncertain dispatch failures or invalid results.
    result = registry.dispatch(hive_request)
    if (
        result.request_id != task.task_id
        or result.target_node != task.target_id
        or result.action != AgentActionType.HEALTH_CHECK
        or result.status.value != "dry_run"
    ):
        raise RuntimeError("Unexpected or non-dry-run CyberHIVE result")

    # Current upstream AgentActionResult has no correlation_id attribute.
    # Compatibility fallback applies only to genuine attribute absence. If a
    # composed/future result exposes the field, even None must match exactly.
    result_correlation_id = getattr(result, "correlation_id", _MISSING_CORRELATION)
    if (
        result_correlation_id is not _MISSING_CORRELATION
        and result_correlation_id != task.correlation_id
    ):
        raise RuntimeError("CyberHIVE result correlation does not match task")

    return HiveDryRunReceipt(
        request_id=result.request_id,
        correlation_id=task.correlation_id,
        target_id=result.target_node,
        status="dry_run",
        reason="HIVE_DRY_RUN_ONLY",
    )
