import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from os import getpid
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest

import cybercore.action_kernel_hive_bridge as hive_bridge
from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_hive_bridge import InMemoryReplayGuard, run_local_hive_dry_run


@pytest.fixture(autouse=True)
def isolated_process_replay_guard(monkeypatch) -> None:
    # Each test models an independent bridge process/clock history. Calls within
    # one test share the same process guard so sticky rollback/replay state is real.
    monkeypatch.setattr(
        hive_bridge,
        "_PROCESS_REPLAY_GUARD",
        hive_bridge._ExpiringProcessReplayGuard(
            max_entries=hive_bridge._PROCESS_REPLAY_MAX_ENTRIES,
            max_per_actor=hive_bridge._PROCESS_REPLAY_MAX_PER_ACTOR,
        ),
    )


def setup(suffix: str):
    kernel = ActionKernel(
        targets={"local-node": {"synthetic_status": "ok"}},
        allowed_actors=frozenset({"chatgpt:johnny-work"}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
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


def test_process_replay_guard_prunes_expired_claims() -> None:
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)

    assert guard.claim_once("a", deadline_monotonic=101.0, now_monotonic=100.0)
    assert guard.claim_once("b", deadline_monotonic=101.0, now_monotonic=100.0)

    with pytest.raises(PermissionError, match="capacity exhausted"):
        guard.claim_once("c", deadline_monotonic=160.0, now_monotonic=100.0)

    assert guard.claim_once("c", deadline_monotonic=160.0, now_monotonic=102.0)
    assert guard.claim_once("a", deadline_monotonic=160.0, now_monotonic=102.0)


def test_process_replay_guard_monotonic_regression_is_sticky_before_pruning() -> None:
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=3)

    assert guard.claim_once(
        "authorization-a",
        deadline_monotonic=110.0,
        now_monotonic=101.0,
    )
    # A later valid authorization advances the process high-water and prunes A.
    assert guard.claim_once(
        "authorization-b",
        deadline_monotonic=120.0,
        now_monotonic=111.0,
    )

    # Returning to 105 would otherwise make A look live again after pruning.
    with pytest.raises(PermissionError, match="monotonic regression detected"):
        guard.claim_once(
            "authorization-a",
            deadline_monotonic=110.0,
            now_monotonic=105.0,
        )

    # The fence is sticky even if the clock subsequently moves forward again.
    with pytest.raises(PermissionError, match="monotonic regression detected"):
        guard.claim_once(
            "authorization-c",
            deadline_monotonic=130.0,
            now_monotonic=112.0,
        )


def test_process_replay_guard_never_evicts_unexpired_claims() -> None:
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1)

    assert guard.claim_once("kept", deadline_monotonic=160.0, now_monotonic=100.0)
    with pytest.raises(PermissionError, match="capacity exhausted"):
        guard.claim_once("new", deadline_monotonic=160.0, now_monotonic=100.0)
    assert (
        guard.claim_once(
            "kept",
            deadline_monotonic=160.0,
            now_monotonic=100.0,
        )
        is False
    )


def test_process_utc_rollback_fence_is_sticky() -> None:
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)

    assert guard.observe_utc(now) == now
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.observe_utc(now - timedelta(seconds=1))
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        guard.observe_utc(now)


def test_process_utc_observation_is_sampled_under_replay_lock() -> None:
    now = datetime.now(timezone.utc)
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=2)
    calls = 0

    def ordered_sample():
        nonlocal calls
        calls += 1
        assert not guard._lock.acquire(blocking=False)
        return now

    assert guard.observe_utc(ordered_sample) == now
    assert calls == 1


def test_forward_utc_expiry_then_rollback_stays_fenced_before_claim(
    monkeypatch,
) -> None:
    task, kernel = setup("forward-expiry-sticky-fence")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    current = [task.expires_at + timedelta(seconds=1)]
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: current[0])
    durable = InMemoryReplayGuard()

    class Forbidden:
        def dispatch(self, _):
            raise AssertionError("Expired or rolled-back authorization must not dispatch")

    with pytest.raises(PermissionError, match="Task authorization expired"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=durable,
        )

    current[0] = task.expires_at - timedelta(seconds=1)
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Forbidden(),
            replay_guard=InMemoryReplayGuard(),
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is True


def test_process_replay_guard_does_not_retain_already_expired_claim() -> None:
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1)

    assert guard.claim_once("expired", deadline_monotonic=100.0, now_monotonic=100.0)
    assert guard.claim_once(
        "fresh",
        deadline_monotonic=160.0,
        now_monotonic=100.0,
    )


def test_process_replay_quota_isolated_by_trusted_actor() -> None:
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=4, max_per_actor=1)

    assert guard.claim_once(
        "alice-1",
        deadline_monotonic=220.0,
        now_monotonic=100.0,
        actor="alice",
    )
    with pytest.raises(PermissionError, match="Actor replay guard capacity exhausted"):
        guard.claim_once(
            "alice-2",
            deadline_monotonic=220.0,
            now_monotonic=100.0,
            actor="alice",
        )
    assert guard.claim_once(
        "bob-1",
        deadline_monotonic=220.0,
        now_monotonic=100.0,
        actor="bob",
    )
    assert (
        guard.claim_once(
            "bob-1",
            deadline_monotonic=220.0,
            now_monotonic=100.0,
            actor="bob",
        )
        is False
    )


def test_wall_clock_forward_then_backward_cannot_prune_process_replay_claim(
    monkeypatch,
) -> None:
    original, original_kernel = setup("wall-clock-prune-original")
    original_receipt = original_kernel.execute(original, trusted_actor=original.actor)
    original_receipt = replace(
        original_receipt,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    trigger, trigger_kernel = setup("wall-clock-prune-trigger")
    trigger = replace(
        trigger,
        expires_at=trigger.requested_at + timedelta(minutes=4),
    )
    trigger_receipt = trigger_kernel.execute(trigger, trusted_actor=trigger.actor)
    trigger_receipt = replace(
        trigger_receipt,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=120.0,
        authorization_process_id=getpid(),
    )
    action = _install_fake_hive(monkeypatch)
    mono = 100.0
    wall = original.expires_at - timedelta(seconds=1)
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: mono)
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: wall)
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

    assert (
        run_local_hive_dry_run(
            original,
            trusted_actor=original.actor,
            kernel_receipt=original_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        ).status
        == "dry_run"
    )

    # A forward wall-clock jump beyond the first task's UTC expiry must not
    # prune its process-local replay claim while its monotonic grant remains live.
    wall = original.expires_at + timedelta(seconds=1)
    mono = 101.0
    assert (
        run_local_hive_dry_run(
            trigger,
            trusted_actor=trigger.actor,
            kernel_receipt=trigger_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        ).status
        == "dry_run"
    )

    # Correct the wall clock backward and replace the caller-provided guard.
    # PR #150's process-owned sticky UTC fence now rejects before replay lookup.
    wall = original.expires_at - timedelta(seconds=1)
    mono = 102.0
    with pytest.raises(PermissionError, match="UTC rollback detected"):
        run_local_hive_dry_run(
            original,
            trusted_actor=original.actor,
            kernel_receipt=original_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        )
    assert calls == 2


def test_bridge_monotonic_regression_after_prune_cannot_replay(
    monkeypatch,
) -> None:
    original, original_kernel = setup("monotonic-prune-original")
    original_receipt = original_kernel.execute(
        original,
        trusted_actor=original.actor,
    )
    original_receipt = replace(
        original_receipt,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )

    trigger, trigger_kernel = setup("monotonic-prune-trigger")
    trigger_receipt = trigger_kernel.execute(
        trigger,
        trusted_actor=trigger.actor,
    )
    trigger_receipt = replace(
        trigger_receipt,
        authorization_floor_monotonic=111.0,
        authorization_deadline_monotonic=120.0,
        authorization_process_id=getpid(),
    )

    action = _install_fake_hive(monkeypatch)
    monotonic_now = 101.0
    wall = max(original.requested_at, trigger.requested_at) + timedelta(seconds=1)
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: monotonic_now)
    monkeypatch.setattr(hive_bridge, "_utc_now", lambda: wall)
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

    assert (
        run_local_hive_dry_run(
            original,
            trusted_actor=original.actor,
            kernel_receipt=original_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        ).status
        == "dry_run"
    )

    # Advance beyond A's deadline. Claiming B prunes A at process high-water 111.
    monotonic_now = 111.0
    assert (
        run_local_hive_dry_run(
            trigger,
            trusted_actor=trigger.actor,
            kernel_receipt=trigger_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        ).status
        == "dry_run"
    )

    # UTC never moved backward and A's local receipt checks would accept 105.
    # The process guard must nevertheless reject the monotonic regression before
    # any replay pruning/claim can resurrect A through a replacement durable guard.
    monotonic_now = 105.0
    with pytest.raises(PermissionError, match="monotonic regression detected"):
        run_local_hive_dry_run(
            original,
            trusted_actor=original.actor,
            kernel_receipt=original_receipt,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        )

    assert calls == 2


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


def test_future_dated_request_is_denied_before_process_replay_quota() -> None:
    task, kernel = setup("future-dated-lifetime")
    future = datetime.now(timezone.utc) + timedelta(days=365)
    altered = replace(
        task,
        requested_at=future,
        expires_at=future + timedelta(minutes=2),
    )

    denied = kernel.execute(altered, trusted_actor=altered.actor)

    assert denied.status == "DENIED"
    assert denied.reason == "INVALID_TIME"
    assert denied.authorization_deadline_monotonic is None
    assert denied.authorization_process_id is None


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
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    guard = hive_bridge._ExpiringProcessReplayGuard(max_entries=1, max_per_actor=1)
    assert guard.claim_once(
        "other",
        deadline_monotonic=110.0,
        now_monotonic=100.0,
        actor=task.actor,
    )
    monkeypatch.setattr(hive_bridge, "_PROCESS_REPLAY_GUARD", guard)
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0)

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


def test_rejects_receipt_without_process_local_deadline() -> None:
    task, kernel = setup("missing-monotonic-deadline")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    legacy = replace(
        allowed,
        authorization_floor_monotonic=None,
        authorization_deadline_monotonic=None,
        authorization_process_id=None,
    )

    with pytest.raises(PermissionError, match="monotonic authorization deadline"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=legacy,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


@pytest.mark.parametrize(
    ("deadline", "process_id"),
    [(float("nan"), getpid()), (float("inf"), getpid()), (100.0, getpid() + 1)],
)
def test_rejects_invalid_or_foreign_process_deadline(deadline, process_id) -> None:
    task, kernel = setup(f"invalid-monotonic-{deadline}-{process_id}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    invalid = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=deadline,
        authorization_process_id=process_id,
    )

    with pytest.raises(PermissionError, match="monotonic authorization deadline"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=invalid,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


def test_monotonic_deadline_equality_fails_closed(monkeypatch) -> None:
    task, kernel = setup("monotonic-equality")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    deadline = 100.0
    allowed = replace(
        allowed,
        authorization_floor_monotonic=99.0,
        authorization_deadline_monotonic=deadline,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: deadline)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )

    with pytest.raises(PermissionError, match="expired before dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


def test_monotonic_floor_equality_is_allowed(monkeypatch) -> None:
    task, kernel = setup("monotonic-floor-equality")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )

    class Registry:
        def dispatch(self, incoming):
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    assert (
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=InMemoryReplayGuard(),
        ).status
        == "dry_run"
    )


@pytest.mark.parametrize("rollback_seconds", [7, 60])
def test_same_pid_monotonic_regression_with_utc_rollback_fails_closed(
    monkeypatch, rollback_seconds: int
) -> None:
    task, kernel = setup(f"monotonic-regression-rollback-{rollback_seconds}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 99.0)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=rollback_seconds),
    )
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="monotonic clock regressed before dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


def test_pid_change_between_bridge_boundaries_fails_closed(monkeypatch) -> None:
    task, kernel = setup("pid-change-boundary")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=4242,
    )
    pids = iter((4242, 4242, 4243))
    monkeypatch.setattr(hive_bridge, "getpid", lambda: next(pids))
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="process changed before replay claim"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


@pytest.mark.parametrize("current", [float("nan"), float("inf")])
def test_nonfinite_current_monotonic_fails_closed(monkeypatch, current: float) -> None:
    task, kernel = setup(f"nonfinite-current-{current}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: current)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )

    with pytest.raises(PermissionError, match="monotonic clock regressed before dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=InMemoryReplayGuard(),
        )


def test_monotonic_regression_during_blocking_claim_fails_closed(monkeypatch) -> None:
    task, kernel = setup("monotonic-regression-during-claim")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    current = [100.0]
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: current[0])
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )
    durable = InMemoryReplayGuard()

    class BlockingGuard:
        def claim_once(self, key):
            claimed = durable.claim_once(key)
            current[0] = 99.0
            return claimed

    with pytest.raises(PermissionError, match="monotonic clock regressed during replay claim"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=BlockingGuard(),
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is False


def test_monotonic_regression_during_dispatch_fails_closed(monkeypatch) -> None:
    task, kernel = setup("monotonic-regression-during-dispatch")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    current = [100.0]
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=110.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: current[0])
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )
    durable = InMemoryReplayGuard()

    class Registry:
        def dispatch(self, incoming):
            current[0] = 99.0
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    with pytest.raises(PermissionError, match="monotonic clock regressed during dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=durable,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is False


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
            task.expires_at - timedelta(seconds=2),
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
            task.expires_at - timedelta(seconds=4),
            task.expires_at - timedelta(seconds=3),
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


@pytest.mark.parametrize("rollback_seconds", [7, 60])
def test_partial_and_full_utc_rollback_cannot_extend_monotonic_deadline(
    monkeypatch, rollback_seconds: int
) -> None:
    task, kernel = setup(f"utc-rollback-{rollback_seconds}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    elapsed = 0.0
    deadline = 105.0
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=deadline,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0 + elapsed)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=rollback_seconds),
    )
    guard = InMemoryReplayGuard()

    class Registry:
        def dispatch(self, incoming):
            nonlocal elapsed
            elapsed = 6.0
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    with pytest.raises(PermissionError, match="expired during dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is False


def test_delay_before_bridge_entry_consumes_monotonic_budget(monkeypatch) -> None:
    task, kernel = setup("delay-before-bridge")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=105.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 105.0)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )
    guard = InMemoryReplayGuard()

    with pytest.raises(PermissionError, match="expired before dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=None,
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is True


@pytest.mark.parametrize("claim_elapsed", [4.0, 6.0])
def test_blocking_claim_obeys_kernel_monotonic_deadline(monkeypatch, claim_elapsed: float) -> None:
    task, kernel = setup(f"blocking-claim-{claim_elapsed}")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    _install_fake_hive(monkeypatch)
    elapsed = 0.0
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=105.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0 + elapsed)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=30),
    )
    durable = InMemoryReplayGuard()

    class BlockingGuard:
        def claim_once(self, key):
            nonlocal elapsed
            claimed = durable.claim_once(key)
            elapsed = claim_elapsed
            return claimed

    class Registry:
        def dispatch(self, _):
            raise AssertionError("Expired claim must never dispatch")

    if claim_elapsed >= 5.0:
        with pytest.raises(PermissionError, match="expired during replay claim"):
            run_local_hive_dry_run(
                task,
                trusted_actor=task.actor,
                kernel_receipt=allowed,
                registry=Registry(),
                replay_guard=BlockingGuard(),
            )
    else:
        # The claim completed before the absolute deadline. A no-op dispatch
        # failure proves the bridge reached dispatch without resetting budget.
        with pytest.raises(AssertionError, match="Expired claim must never dispatch"):
            run_local_hive_dry_run(
                task,
                trusted_actor=task.actor,
                kernel_receipt=allowed,
                registry=Registry(),
                replay_guard=BlockingGuard(),
            )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert durable.claim_once(key) is False


def test_dispatch_crossing_monotonic_deadline_is_rejected_with_claim_consumed(
    monkeypatch,
) -> None:
    task, kernel = setup("dispatch-crosses-deadline")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    action = _install_fake_hive(monkeypatch)
    elapsed = 0.0
    allowed = replace(
        allowed,
        authorization_floor_monotonic=100.0,
        authorization_deadline_monotonic=105.0,
        authorization_process_id=getpid(),
    )
    monkeypatch.setattr(hive_bridge, "monotonic", lambda: 100.0 + elapsed)
    monkeypatch.setattr(
        hive_bridge,
        "_utc_now",
        lambda: task.expires_at - timedelta(seconds=60),
    )
    guard = InMemoryReplayGuard()

    class Registry:
        def dispatch(self, incoming):
            nonlocal elapsed
            elapsed = 5.0
            return SimpleNamespace(
                request_id=incoming.id,
                target_node=incoming.target_node,
                action=action.HEALTH_CHECK,
                status=SimpleNamespace(value="dry_run"),
            )

    with pytest.raises(PermissionError, match="expired during dispatch"):
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=allowed,
            registry=Registry(),
            replay_guard=guard,
        )

    key = f"{task.actor}:{task.task_id}:{task.correlation_id}"
    assert guard.claim_once(key) is False
