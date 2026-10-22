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


def test_rejects_expired_task_before_optional_runtime_work() -> None:
    task, kernel = setup("already-expired")
    allowed = kernel.execute(task, trusted_actor=task.actor)
    expired = replace(task, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    with pytest.raises(PermissionError, match="expired"):
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
            task.expires_at - timedelta(seconds=2),
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
