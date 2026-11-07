import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest

import cybercore.action_kernel_hive_bridge as hive_bridge
from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_hive_bridge import InMemoryReplayGuard, run_local_hive_dry_run


@pytest.fixture(autouse=True)
def isolated_process_replay_guard(monkeypatch) -> None:
    # Independent tests represent independent processes/clock histories.
    # Keep this same guard for every call within a test, including replay and races.
    monkeypatch.setattr(
        hive_bridge,
        "_PROCESS_REPLAY_GUARD",
        hive_bridge._ExpiringProcessReplayGuard(
            max_entries=hive_bridge._PROCESS_REPLAY_MAX_ENTRIES,
            max_per_actor=hive_bridge._PROCESS_REPLAY_MAX_PER_ACTOR,
        ),
    )


def setup(suffix: str):
    now = datetime.now(timezone.utc)
    task = TaskRequest(
        task_id=f"hive-test-{suffix}",
        correlation_id=f"corr-hive-{suffix}",
        actor="chatgpt:johnny-work",
        capability="diagnostics.synthetic_status.v1",
        target_id="local-node",
        arguments={},
        requested_at=now,
        expires_at=now + timedelta(minutes=2),
        provenance=Provenance("cybercore", "test", "local", now),
    )
    kernel = ActionKernel(
        targets={"local-node": {"synthetic_status": "ok"}},
        allowed_actors=frozenset({"chatgpt:johnny-work"}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    return task, kernel


def _install_fake_hive(monkeypatch):
    class Action(Enum):
        HEALTH_CHECK = "health_check"

    class Request:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setitem(sys.modules, "cyberhive_core", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules,
        "cyberhive_core.node_agent",
        SimpleNamespace(AgentActionRequest=Request, AgentActionType=Action),
    )
    return Action


def test_rejects_denied_task_without_dispatch() -> None:
    task, kernel = setup("denied")
    denied = kernel.execute(task, trusted_actor="chatgpt:intruder")
    with pytest.raises(PermissionError):
        run_local_hive_dry_run(
            task,
            trusted_actor="chatgpt:intruder",
            kernel_receipt=denied,
            registry=None,
        )


def test_rejects_receipt_replay_between_tasks() -> None:
    task, kernel = setup("cross-task")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    altered = TaskRequest(
        task_id="other",
        correlation_id=task.correlation_id,
        actor=task.actor,
        capability=task.capability,
        target_id=task.target_id,
        arguments=task.arguments,
        requested_at=task.requested_at,
        expires_at=task.expires_at,
        provenance=task.provenance,
    )
    with pytest.raises(PermissionError):
        run_local_hive_dry_run(
            altered,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
        )


def test_local_registry_receives_only_typed_dry_run(monkeypatch) -> None:
    task, kernel = setup("typed")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)

    class Registry:
        def dispatch(self, incoming):
            assert incoming.dry_run is True
            assert incoming.action is action.HEALTH_CHECK
            assert incoming.approval_tokens == ()
            assert incoming.payload == {}
            assert incoming.requested_by == task.actor
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=incoming.action,
                status=SimpleNamespace(value="dry_run"),
            )

    receipt = run_local_hive_dry_run(
        task,
        trusted_actor=task.actor,
        kernel_receipt=allowed,
        registry=Registry(),
        replay_guard=InMemoryReplayGuard(),
    )
    assert receipt.status == "dry_run"
    assert receipt.reason == "HIVE_DRY_RUN_ONLY"


def test_requires_replay_guard_before_dispatch() -> None:
    task, kernel = setup("requires-guard")
    allowed = kernel.execute(task, trusted_actor=task.actor)

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Must not dispatch")

    with pytest.raises(PermissionError, match="replay guard required"):
        run_local_hive_dry_run(
            task, trusted_actor=task.actor, kernel_receipt=allowed, registry=Forbidden()
        )


def test_replayed_durable_claim_fails_closed(monkeypatch) -> None:
    task, kernel = setup("durable-replay")
    _install_fake_hive(monkeypatch)
    allowed = kernel.execute(task, trusted_actor=task.actor)
    guard = InMemoryReplayGuard()
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Must not dispatch")

    with pytest.raises(PermissionError, match="already consumed"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=guard,
        )


def test_fresh_replay_guard_cannot_bypass_process_claim(monkeypatch) -> None:
    task, kernel = setup("fresh-guard-replay")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    calls = 0

    class Registry:
        def dispatch(self, incoming):
            nonlocal calls
            calls += 1
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    run_local_hive_dry_run(
        task,
        trusted_actor=task.actor,
        kernel_receipt=allowed,
        registry=Registry(),
        replay_guard=InMemoryReplayGuard(),
    )
    with pytest.raises(PermissionError, match="already consumed"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        )

    assert calls == 1


def test_concurrent_fresh_guards_cannot_bypass_process_claim(monkeypatch) -> None:
    task, kernel = setup("concurrent-fresh-guards")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    start = Barrier(2)
    calls_lock = Lock()
    calls = 0

    class Registry:
        def dispatch(self, incoming):
            nonlocal calls
            with calls_lock:
                calls += 1
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    def invoke(_):
        start.wait(timeout=5)
        try:
            return run_local_hive_dry_run(
                task,
                trusted_actor=task.actor,
                kernel_receipt=allowed,
                registry=Registry(),
                replay_guard=InMemoryReplayGuard(),
            ).status
        except PermissionError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, range(2)))

    assert sorted(outcomes) == ["Authorization already consumed", "dry_run"]
    assert calls == 1


def test_process_replay_guard_prunes_expired_claims(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    elapsed = 0.0
    monkeypatch.setattr(hive_bridge, "_replay_monotonic", lambda: elapsed)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)

    assert guard.claim_once("a", expires_at=now + timedelta(seconds=1), now=now)
    assert guard.claim_once("b", expires_at=now + timedelta(seconds=1), now=now)

    with pytest.raises(PermissionError, match="capacity exhausted"):
        guard.claim_once("c", expires_at=now + timedelta(minutes=1), now=now)

    # UTC alone cannot prune a claim; a full monotonic retention horizon can.
    later = now + timedelta(seconds=2)
    with pytest.raises(PermissionError, match="capacity exhausted"):
        guard.claim_once("c", expires_at=later + timedelta(minutes=1), now=later)
    elapsed = 301.0
    assert guard.claim_once("c", expires_at=later + timedelta(minutes=1), now=later)
    assert guard.claim_once("a", expires_at=later + timedelta(minutes=1), now=later)


def test_process_replay_guard_never_evicts_unexpired_claims() -> None:
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1)

    assert guard.claim_once("kept", expires_at=now + timedelta(minutes=1), now=now)
    with pytest.raises(PermissionError, match="capacity exhausted"):
        guard.claim_once("new", expires_at=now + timedelta(minutes=1), now=now)
    assert (
        guard.claim_once(
            "kept",
            expires_at=now + timedelta(minutes=1),
            now=now,
        )
        is False
    )


def test_process_replay_guard_rejects_expiry_and_retains_tombstone(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    elapsed = 100.0
    monkeypatch.setattr(hive_bridge, "_replay_monotonic", lambda: elapsed)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1)

    with pytest.raises(PermissionError, match="expired during replay claim"):
        guard.claim_once("expired", expires_at=now, now=now)
    # UTC rollback disables the process guard rather than reviving any claim.
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("expired", expires_at=now, now=now - timedelta(seconds=1))
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("fresh", expires_at=now + timedelta(minutes=1), now=now)
    elapsed = 401.0
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("fresh", expires_at=now + timedelta(minutes=1), now=now)


def test_process_replay_quota_isolated_by_trusted_actor() -> None:
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=4, max_per_actor=1)
    expires_at = now + timedelta(minutes=2)

    assert guard.claim_once("alice-1", expires_at=expires_at, now=now, actor="alice")
    with pytest.raises(PermissionError, match="Actor replay guard capacity exhausted"):
        guard.claim_once("alice-2", expires_at=expires_at, now=now, actor="alice")
    assert guard.claim_once("bob-1", expires_at=expires_at, now=now, actor="bob")
    assert guard.claim_once("bob-1", expires_at=expires_at, now=now, actor="bob") is False


def test_rejects_overlong_authorization_before_optional_runtime_or_claim() -> None:
    task, kernel = setup("overlong-lifetime")
    long_task = replace(task, expires_at=task.requested_at + timedelta(days=1))
    allowed = kernel.execute(long_task, trusted_actor=long_task.actor)
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="lifetime exceeds policy"):
        run_local_hive_dry_run(
            long_task,
            trusted_actor=long_task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )
    key = f"{long_task.actor}:{long_task.task_id}:{long_task.correlation_id}"
    assert guard.claim_once(key) is True


def test_future_dated_request_cannot_pin_process_replay_quota() -> None:
    task, kernel = setup("future-dated-lifetime")
    future = datetime.now(timezone.utc) + timedelta(days=365)
    altered = replace(
        task,
        requested_at=future,
        expires_at=future + timedelta(minutes=2),
    )
    # Current kernel historically permits a future requested_at, but the
    # bridge must not use untrusted request time as replay retention authority.
    allowed = kernel.execute(altered, trusted_actor=altered.actor)
    assert allowed.status == "EXECUTED"
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="lifetime exceeds policy"):
        run_local_hive_dry_run(
            altered,
            trusted_actor=altered.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )

    key = f"{altered.actor}:{altered.task_id}:{altered.correlation_id}"
    assert guard.claim_once(key) is True


def test_expiry_lifetime_uses_receipt_clock_not_old_request_time() -> None:
    task, kernel = setup("receipt-clock-bound")
    altered = replace(
        task,
        requested_at=task.requested_at - timedelta(days=1),
        expires_at=task.expires_at + timedelta(minutes=10),
    )
    allowed = kernel.execute(altered, trusted_actor=altered.actor)
    assert allowed.status == "EXECUTED"
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="lifetime exceeds policy"):
        run_local_hive_dry_run(
            altered,
            trusted_actor=altered.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )
    key = f"{altered.actor}:{altered.task_id}:{altered.correlation_id}"
    assert guard.claim_once(key) is True


def test_process_capacity_rejects_before_durable_claim(monkeypatch) -> None:
    task, kernel = setup("capacity-before-durable")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1, max_per_actor=1)
    assert guard.claim_once(
        "other", expires_at=now + timedelta(minutes=2), now=now, actor=task.actor
    )
    monkeypatch.setattr(hive_bridge, "_PROCESS_REPLAY_GUARD", guard)

    class CountingDurable:
        calls = 0

        def claim_once(self, _: str) -> bool:
            self.calls += 1
            return True

    durable = CountingDurable()

    with pytest.raises(PermissionError, match="capacity exhausted"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=durable,
        )
    assert durable.calls == 0


def test_replay_guard_backend_failure_fails_closed(monkeypatch) -> None:
    task, kernel = setup("guard-failure")
    _install_fake_hive(monkeypatch)
    allowed = kernel.execute(task, trusted_actor=task.actor)

    class BrokenGuard:
        def claim_once(self, _: str) -> bool:
            raise OSError("store unavailable")

    with pytest.raises(PermissionError, match="guard unavailable"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=BrokenGuard(),
        )


def test_retains_process_claim_after_uncertain_dispatch_failure(monkeypatch) -> None:
    task, kernel = setup("uncertain-dispatch")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)

    class FailingRegistry:
        def dispatch(self, _):
            raise RuntimeError("dispatch outcome unknown")

    with pytest.raises(RuntimeError, match="outcome unknown"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=FailingRegistry(),
            replay_guard=InMemoryReplayGuard(),
        )

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Consumed authorization must not dispatch")

    with pytest.raises(PermissionError, match="already consumed"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=InMemoryReplayGuard(),
        )


@pytest.mark.parametrize("shift_seconds", [-30, 30])
def test_rejects_altered_authorization_expiry_before_claim_or_dispatch(
    shift_seconds: int,
) -> None:
    task, kernel = setup(f"altered-expiry-{shift_seconds}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    altered = replace(task, expires_at=task.expires_at + timedelta(seconds=shift_seconds))
    guard = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Altered authorization must never dispatch")

    with pytest.raises(PermissionError, match="authorization expiry do not match"):
        run_local_hive_dry_run(
            altered,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


def test_rejects_receipt_without_bound_authorization_expiry() -> None:
    task, kernel = setup("missing-receipt-expiry")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    legacy = replace(allowed, authorization_expires_at=None)

    with pytest.raises(PermissionError, match="authorization expiry do not match"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=legacy,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


def test_rejects_expired_task_before_optional_runtime_work() -> None:
    task, kernel = setup("already-expired")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    expired = replace(task, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    with pytest.raises(PermissionError, match="authorization expiry do not match"):
        run_local_hive_dry_run(
            expired,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


def test_rechecks_expiry_immediately_before_claim_and_dispatch(monkeypatch) -> None:
    task, kernel = setup("boundary-expiry")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    times = iter(
        (
            task.expires_at - timedelta(seconds=1),
            task.expires_at - timedelta(seconds=1),
            task.expires_at + timedelta(seconds=1),
        )
    )
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: next(times))

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Expired authorization must not dispatch")

    with pytest.raises(PermissionError, match="expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=InMemoryReplayGuard(),
        )


def test_rechecks_expiry_after_claim_before_dispatch(monkeypatch) -> None:
    task, kernel = setup("post-claim-expiry")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    times = iter(
        (
            task.expires_at - timedelta(seconds=3),
            task.expires_at - timedelta(seconds=3),
            task.expires_at - timedelta(seconds=2),
            task.expires_at - timedelta(seconds=1),
            task.expires_at - timedelta(seconds=1),
            task.expires_at + timedelta(seconds=1),
        )
    )
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: next(times))
    guard = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Task expired after claim must not dispatch")

    with pytest.raises(PermissionError, match="expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is False


def test_rejects_result_returned_after_authorization_deadline(monkeypatch) -> None:
    task, kernel = setup("post-dispatch-expiry")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    times = iter(
        (
            task.expires_at - timedelta(seconds=5),
            task.expires_at - timedelta(seconds=5),
            task.expires_at - timedelta(seconds=4),
            task.expires_at - timedelta(seconds=3),
            task.expires_at - timedelta(seconds=2),
            task.expires_at - timedelta(seconds=2),
            task.expires_at + timedelta(seconds=1),
        )
    )
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: next(times))
    guard = InMemoryReplayGuard()

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    with pytest.raises(PermissionError, match="expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is False


def test_rejects_mismatched_result_correlation(monkeypatch) -> None:
    task, kernel = setup("wrong-correlation")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
                correlation_id="wrong-correlation",
            )

    with pytest.raises(RuntimeError, match="correlation"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        )


def test_rejects_null_result_correlation_when_attribute_is_present(monkeypatch) -> None:
    task, kernel = setup("null-correlation")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
                correlation_id=None,
            )

    with pytest.raises(RuntimeError, match="correlation"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        )


def test_current_upstream_result_without_correlation_remains_supported(monkeypatch) -> None:
    task, kernel = setup("upstream-no-correlation")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    receipt = run_local_hive_dry_run(
        task,
        trusted_actor=task.actor,
        kernel_receipt=allowed,
        registry=Registry(),
        replay_guard=InMemoryReplayGuard(),
    )

    assert receipt.correlation_id == task.correlation_id


@pytest.mark.parametrize(
    ("elapsed", "wall_offset", "rejected"),
    [(1.0, -60, False), (2.0, -60, True), (3.0, -60, True), (1.0, 1, True)],
)
def test_dispatch_deadline_survives_wall_clock_corrections(
    monkeypatch, elapsed: float, wall_offset: int, rejected: bool
) -> None:
    task, kernel = setup(f"clock-correction-{elapsed}-{wall_offset}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    wall_after = task.expires_at + timedelta(seconds=wall_offset)
    times = iter(
        (
            task.expires_at - timedelta(seconds=5),
            task.expires_at - timedelta(seconds=5),
            task.expires_at - timedelta(seconds=2),
            task.expires_at - timedelta(seconds=2),
            task.expires_at - timedelta(seconds=2),
            task.expires_at - timedelta(seconds=2),
            wall_after,
        )
    )
    ticks = iter((100.0, 100.0, 100.0, 100.0, 100.0 + elapsed))
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: next(times, wall_after))
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: next(ticks, 100.0 + elapsed))
    guard = InMemoryReplayGuard()
    calls = 0

    class Registry:
        def dispatch(self, incoming):
            nonlocal calls
            calls += 1
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    def invoke(replay_guard):
        return run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=replay_guard,
        )

    if rejected:
        with pytest.raises(PermissionError, match="expired"):
            invoke(guard)
    else:
        assert invoke(guard).status == "dry_run"

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is False
    # Even replacing the supplied guard cannot replay under the rolled-back clock.
    with pytest.raises(PermissionError, match="UTC rollback detected|expired|already consumed"):
        invoke(InMemoryReplayGuard())
    assert calls == 1


@pytest.mark.parametrize("rollback_at", ["anchor", "second_utc"])
def test_rollback_between_deadline_samples_cannot_extend_budget(
    monkeypatch, rollback_at: str
) -> None:
    task, kernel = setup(f"sampling-rollback-{rollback_at}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    utc_calls = 0
    mono_calls = 0
    rolled_back = False

    def utc_now():
        nonlocal utc_calls, rolled_back
        utc_calls += 1
        if utc_calls <= 3:
            return task.expires_at - timedelta(seconds=2)
        if rollback_at == "second_utc" and utc_calls == 5:
            rolled_back = True
        return task.expires_at - timedelta(seconds=62 if rolled_back else 2)

    def monotonic_now():
        nonlocal mono_calls, rolled_back
        mono_calls += 1
        if rollback_at == "anchor" and mono_calls == 2:
            rolled_back = True
        return {1: 100.0, 2: 100.0, 3: 103.0}.get(mono_calls, 103.0)

    monkeypatch.setattr(hive_bridge, "_utc_now", utc_now)
    monkeypatch.setattr(hive_bridge, "monotonic", monotonic_now)
    guard = InMemoryReplayGuard()

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    with pytest.raises(PermissionError, match="expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=guard,
        )
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


@pytest.mark.parametrize("claim_elapsed", [1.0, 3.0])
def test_blocking_claim_cannot_extend_deadline_with_utc_rollback(
    monkeypatch, claim_elapsed: float
) -> None:
    task, kernel = setup(f"claim-rollback-{claim_elapsed}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    elapsed = 0.0
    rolled_back = False
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0 + elapsed)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=61 if rolled_back else 1),
    )
    durable = InMemoryReplayGuard()

    class BlockingGuard:
        def claim_once(self, key):
            nonlocal elapsed, rolled_back
            claimed = durable.claim_once(key)
            elapsed = claim_elapsed
            rolled_back = True
            return claimed

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Expired claim must never dispatch")

    with pytest.raises(PermissionError, match="expired during replay claim"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=BlockingGuard(),
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is False
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=InMemoryReplayGuard(),
        )


@pytest.mark.parametrize("setup_elapsed", [1.0, 3.0])
def test_optional_setup_cannot_restart_authorization_budget(
    monkeypatch, setup_elapsed: float
) -> None:
    task, kernel = setup(f"setup-rollback-{setup_elapsed}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    elapsed = 0.0
    rolled_back = False
    import_module = hive_bridge.import_module
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0 + elapsed)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=61 if rolled_back else 1),
    )

    def delayed_import(name):
        nonlocal elapsed, rolled_back
        elapsed = setup_elapsed
        rolled_back = True
        return import_module(name)

    monkeypatch.setattr(hive_bridge, "import_module", delayed_import)
    guard = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Expired setup must never dispatch")

    with pytest.raises(PermissionError, match="expired before replay claim"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=guard,
        )
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


@pytest.mark.parametrize("setup_elapsed", [1.0, 3.0])
def test_utc_rollback_before_first_monotonic_sample_fails_closed(
    monkeypatch, setup_elapsed: float
) -> None:
    task, kernel = setup(f"initial-sample-rollback-{setup_elapsed}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    elapsed = 0.0
    rolled_back = False
    import_module = hive_bridge.import_module

    def monotonic_now():
        nonlocal rolled_back
        rolled_back = True
        return 100.0 + elapsed

    monkeypatch.setattr(hive_bridge, "monotonic", monotonic_now)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=61 if rolled_back else 1),
    )

    def delayed_import(name):
        nonlocal elapsed
        elapsed = setup_elapsed
        return import_module(name)

    monkeypatch.setattr(hive_bridge, "import_module", delayed_import)
    guard = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Initial-sample rollback must not dispatch")

    with pytest.raises(PermissionError, match="expired: UTC clock moved backward"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=guard,
        )
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


def test_preanchor_utc_rollback_rejects_without_claim_or_dispatch(monkeypatch) -> None:
    task, kernel = setup("preanchor-rollback-hardening")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    rollback = False

    def wall_time():
        return task.expires_at - timedelta(seconds=61 if rollback else 1)

    def clock():
        nonlocal rollback
        # Simulate suspension between first UTC sample and monotonic anchor.
        rollback = True
        return 100.0

    monkeypatch.setattr(hive_bridge, "_utc_now", wall_time)
    monkeypatch.setattr(hive_bridge, "monotonic", clock)
    durable = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("UTC rollback must not dispatch")

    with pytest.raises(PermissionError, match="expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=durable,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is True  # Rejected before claiming.


def test_forward_utc_during_process_claim_never_allows_replay(monkeypatch) -> None:
    task, kernel = setup("claim-forward-clock-hardening")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    calls = 0
    clock_rolled_back = False
    durable = InMemoryReplayGuard()

    def utc_now():
        nonlocal calls, clock_rolled_back
        calls += 1
        if calls == 5:
            clock_rolled_back = True
            return task.expires_at + timedelta(seconds=1)
        return task.expires_at - timedelta(seconds=61 if clock_rolled_back else 1)

    monkeypatch.setattr(hive_bridge, "_utc_now", utc_now)
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0)

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Expired claim or replay must not dispatch")

    with pytest.raises(PermissionError, match="expired during replay claim"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=durable,
        )
    # The forward sample did not call durable storage, but the process claim
    # survives UTC rollback and denies a replacement durable guard.
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is True
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=InMemoryReplayGuard(),
        )


def test_forward_utc_jump_cannot_prune_prior_process_replay_claim(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(hive_bridge, "_replay_monotonic", lambda: 100.0)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=3)

    assert guard.claim_once("prior", expires_at=now + timedelta(minutes=1), now=now)
    # An NTP forward step cannot be used to erase the previous replay claim.
    with pytest.raises(PermissionError, match="expired during replay claim"):
        guard.claim_once(
            "later", expires_at=now + timedelta(minutes=1), now=now + timedelta(minutes=2)
        )
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("prior", expires_at=now + timedelta(minutes=1), now=now)
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("later", expires_at=now + timedelta(minutes=1), now=now)


def test_replay_guard_stays_fenced_after_300s_pruning_and_utc_rollback(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    elapsed = 0.0
    monkeypatch.setattr(hive_bridge, "_replay_monotonic", lambda: elapsed)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)
    assert guard.claim_once("prior", expires_at=now + timedelta(seconds=1), now=now)

    # More than five monotonic minutes elapsed; a forward UTC sample prunes
    # the key, but this observed UTC value becomes a process-wide high-water.
    elapsed = 301.0
    future = now + timedelta(minutes=6)
    with pytest.raises(PermissionError, match="expired during replay claim"):
        guard.claim_once("probe", expires_at=now + timedelta(minutes=1), now=future)

    # A backward correction must not permit reuse of the pruned key.
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("prior", expires_at=now + timedelta(seconds=1), now=now)
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.claim_once("fresh", expires_at=now + timedelta(minutes=10), now=future)


def test_replay_guard_samples_utc_under_its_lock() -> None:
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)
    calls = 0

    def ordered_utc_sample():
        nonlocal calls
        calls += 1
        # The live clock must be sampled while the replay guard owns its lock.
        assert not guard._lock.acquire(blocking=False)
        return now

    assert guard.claim_once(
        "first",
        expires_at=now + timedelta(minutes=1),
        now=ordered_utc_sample,
    )
    assert guard.claim_once(
        "second",
        expires_at=now + timedelta(minutes=1),
        now=ordered_utc_sample,
    )
    assert calls == 2


def test_monotonic_budget_covers_pause_after_first_utc_sample(monkeypatch) -> None:
    task, kernel = setup("partial-rollback-before-anchor")
    receipt = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    ticks = iter((100.0, 103.0))
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: next(ticks, 103.0))
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=0.5),
    )
    durable = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("No dispatch after elapsed budget")

    with pytest.raises(PermissionError, match="expired before dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=receipt,
            registry=Forbidden(),
            replay_guard=durable,
        )
    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is True
