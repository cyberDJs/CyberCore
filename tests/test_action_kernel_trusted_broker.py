"""Security regression tests for the trusted local broker boundary."""

from datetime import datetime, timedelta, timezone

from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_hive_bridge import InMemoryReplayGuard
from cybercore.action_kernel_trusted_broker import TrustedLocalHiveBroker


def _task() -> TaskRequest:
    now = datetime.now(timezone.utc)
    return TaskRequest(
        task_id="trusted-broker-1",
        correlation_id="trusted-broker-corr-1",
        actor="trusted-actor",
        capability="diagnostics.synthetic_status.v1",
        target_id="test-node",
        arguments={},
        requested_at=now,
        expires_at=now + timedelta(minutes=2),
        provenance=Provenance("cybercore", "test", "local", now),
    )


def _kernel(*, enabled: bool, events: list) -> ActionKernel:
    return ActionKernel(
        targets={"test-node": {"synthetic_status": "ok"}},
        allowed_actors=frozenset({"trusted-actor"}),
        enabled=enabled,
        evidence_sink=events.append,
    )


def test_broker_denies_spoof_before_kernel_and_dispatch() -> None:
    events = []
    broker = TrustedLocalHiveBroker(
        kernel=_kernel(enabled=True, events=events),
        registry=None,
        replay_guard=InMemoryReplayGuard(),
    )
    result = broker.execute(_task(), authenticated_actor="intruder")
    assert result.status == "DENIED"
    assert result.reason == "ACTOR_MISMATCH"
    assert not events


def test_broker_denied_policy_never_dispatches() -> None:
    events = []
    broker = TrustedLocalHiveBroker(
        kernel=_kernel(enabled=False, events=events),
        registry=None,
        replay_guard=InMemoryReplayGuard(),
    )
    result = broker.execute(_task(), authenticated_actor="trusted-actor")
    assert result.status == "DENIED"
    assert result.reason == "FEATURE_DISABLED"
    assert events


def test_broker_has_no_external_receipt_parameter() -> None:
    from inspect import signature

    names = signature(TrustedLocalHiveBroker.execute).parameters
    assert "kernel_receipt" not in names
    assert "receipt" not in names
    assert list(names) == ["self", "task", "authenticated_actor"]


def test_broker_requires_audit_sink() -> None:
    kernel = ActionKernel(
        targets={"test-node": {"synthetic_status": "ok"}},
        allowed_actors=frozenset({"trusted-actor"}),
        enabled=True,
    )
    broker = TrustedLocalHiveBroker(
        kernel=kernel,
        registry=None,
        replay_guard=InMemoryReplayGuard(),
    )
    result = broker.execute(_task(), authenticated_actor="trusted-actor")
    assert result.status == "DENIED"
    assert result.reason == "AUDIT_UNAVAILABLE"
