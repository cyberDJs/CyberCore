"""Local-only CyberHIVE dry-run bridge for the governed Action Kernel.

The caller supplies a trusted, preconfigured local registry. This module never
opens a network connection, enrolls nodes, or authorizes live actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import import_module
from threading import Lock
from time import monotonic, monotonic as _replay_monotonic
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


class _ExpiringProcessReplayGuard:
    """Bounded process-local replay accelerator.

    Durable replay history remains the responsibility of the caller-provided
    ReplayGuard. This layer retains only still-valid authorizations and fails
    closed instead of evicting an unexpired claim when capacity is exhausted.
    """

    def __init__(self, *, max_entries: int, max_per_actor: int | None = None) -> None:
        if max_entries <= 0:
            raise ValueError("Replay cache capacity must be positive")
        if max_per_actor is not None and max_per_actor <= 0:
            raise ValueError("Per-actor replay capacity must be positive")
        self._max_entries = max_entries
        self._max_per_actor = max_entries if max_per_actor is None else max_per_actor
        self._claimed_until: dict[str, tuple[datetime, str, float]] = {}
        # A bounded cache must not accept old grants after any observed UTC
        # rollback, even if the earlier claim was safely pruned by elapsed time.
        self._max_seen_utc: datetime | None = None
        self._utc_rollback_detected = False
        self._lock = Lock()

    def claim_once(
        self,
        key: str,
        *,
        expires_at: datetime,
        now: datetime,
        actor: str = "",
    ) -> bool:
        with self._lock:
            # Sticky fail-closed state: forward UTC can prune an old claim after
            # its monotonic horizon; a subsequent backward jump must never
            # revive that authorization, including via a replaced durable guard.
            if self._utc_rollback_detected:
                raise PermissionError("Process replay guard UTC rollback detected")
            if self._max_seen_utc is not None and now < self._max_seen_utc:
                self._utc_rollback_detected = True
                raise PermissionError("Process replay guard UTC rollback detected")
            self._max_seen_utc = now
            process_now = _replay_monotonic()
            # UTC jumps are not proof that a claimed authorization elapsed.
            # Retain every claim for at least the maximum trusted lifetime
            # on an independent monotonic clock before pruning by UTC.
            expired_keys = [
                claimed_key
                for claimed_key, (claimed_until, _, claimed_at) in self._claimed_until.items()
                if claimed_until <= now
                and process_now - claimed_at >= _MAX_AUTHORIZATION_LIFETIME.total_seconds()
            ]
            for claimed_key in expired_keys:
                del self._claimed_until[claimed_key]

            if key in self._claimed_until:
                return False

            # Even if UTC leaps forward past expiry, retain a consumed
            # process claim before rejecting: rollback must not enable replay.
            expired_at_claim = expires_at <= now

            if len(self._claimed_until) >= self._max_entries:
                raise PermissionError("Process replay guard capacity exhausted")
            actor_claims = sum(
                1 for _, claimed_actor, _ in self._claimed_until.values() if claimed_actor == actor
            )
            if actor_claims >= self._max_per_actor:
                raise PermissionError("Actor replay guard capacity exhausted")

            self._claimed_until[key] = (expires_at, actor, process_now)
            if expired_at_claim:
                raise PermissionError("Task authorization expired during replay claim")
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
_PROCESS_REPLAY_MAX_ENTRIES = 4096
_PROCESS_REPLAY_MAX_PER_ACTOR = 128
_MAX_AUTHORIZATION_LIFETIME = timedelta(minutes=5)
_PROCESS_REPLAY_GUARD = _ExpiringProcessReplayGuard(
    max_entries=_PROCESS_REPLAY_MAX_ENTRIES,
    max_per_actor=_PROCESS_REPLAY_MAX_PER_ACTOR,
)
_MISSING_CORRELATION = object()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_not_expired(task: TaskRequest) -> datetime:
    now = _utc_now()
    if task.expires_at.tzinfo is None or task.expires_at <= now:
        raise PermissionError("Task authorization expired")
    return now


def _claim_once(
    replay_guard: ReplayGuard,
    key: str,
    *,
    expires_at: datetime,
    actor: str,
) -> None:
    # Reserve the bounded local claim before attempting the irreversible
    # durable claim. A failed/uncertain durable result retains the local claim
    # until expiry: replay denial is safer than an ambiguous second dispatch.
    if not _PROCESS_REPLAY_GUARD.claim_once(
        key,
        expires_at=expires_at,
        now=_utc_now(),
        actor=actor,
    ):
        raise PermissionError("Authorization already consumed")
    try:
        durable_claimed = replay_guard.claim_once(key)
    except Exception as exc:
        raise PermissionError("Replay guard unavailable") from exc
    if not durable_claimed:
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

    # The authorization lifetime must be the one approved by the trusted
    # kernel. A caller must not shorten it to evict a replay claim early, or
    # extend it to dispatch after the original grant expired.
    if (
        kernel_receipt.authorization_expires_at is None
        or kernel_receipt.authorization_expires_at != task.expires_at
    ):
        raise PermissionError("Task and authorization expiry do not match")

    # Bind lifetime to a trusted kernel receipt timestamp, not the
    # caller-controlled requested_at. Otherwise future-dated requests could
    # indefinitely occupy the bounded replay cache.
    if (
        task.requested_at.tzinfo is None
        or kernel_receipt.completed_at.tzinfo is None
        or task.expires_at <= task.requested_at
        or task.requested_at > kernel_receipt.completed_at
        or task.expires_at - kernel_receipt.completed_at > _MAX_AUTHORIZATION_LIFETIME
    ):
        raise PermissionError("Task authorization lifetime exceeds policy")

    # Establish one budget before any optional setup or blocking claim work.
    # Bracket the monotonic anchor with UTC checks. Use the later UTC sample
    # so a rollback between samples cannot inflate the remaining interval.
    # The earlier monotonic bound includes sampling overhead conservatively.
    utc_initial = _assert_not_expired(task)
    sampling_started = monotonic()
    utc_before = _assert_not_expired(task)
    authorization_started = monotonic()
    utc_after = _assert_not_expired(task)
    # A pre-anchor pause followed by UTC rollback is invisible to monotonic
    # elapsed time; reject decreasing UTC samples instead of granting slack.
    if utc_before < utc_initial or utc_after < utc_before:
        raise PermissionError("Task authorization expired: UTC clock moved backward")
    remaining_seconds = (task.expires_at - max(utc_initial, utc_before, utc_after)).total_seconds()
    remaining_seconds -= authorization_started - sampling_started
    if remaining_seconds <= 0:
        raise PermissionError("Task authorization expired before dispatch")

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
    if monotonic() - authorization_started >= remaining_seconds:
        raise PermissionError("Task authorization expired before replay claim")

    key = f"{trusted_actor}:{task.task_id}:{task.correlation_id}"
    _claim_once(replay_guard, key, expires_at=task.expires_at, actor=trusted_actor)

    # Carry the original budget across a potentially blocking durable claim.
    # Claims remain consumed when it expires; do not dispatch or restart it.
    _assert_not_expired(task)
    if monotonic() - authorization_started >= remaining_seconds:
        raise PermissionError("Task authorization expired during replay claim")

    # Both claims intentionally remain consumed after this boundary, including
    # uncertain dispatch failures or invalid/late results.
    result = registry.dispatch(hive_request)

    # The current CyberHIVE NodeAgentRegistry dispatch contract is synchronous
    # and has no cancellation/deadline parameter. Reject a result that returns
    # after authorization expiry instead of accepting late work as success.
    # Claims remain consumed because the dispatch outcome already occurred.
    _assert_not_expired(task)
    # A backward wall-clock correction must not extend in-flight authorization.
    if monotonic() - authorization_started >= remaining_seconds:
        raise PermissionError("Task authorization expired during dispatch")

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
