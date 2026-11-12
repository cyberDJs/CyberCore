"""Integration smoke test using real pinned CyberHIVE classes (not mock types)."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_hive_bridge import InMemoryReplayGuard, run_local_hive_dry_run
from cyberhive_core.node_agent import LocalNodeAgent, NodeAgentRegistry, NodeDescriptor


def test_actual_hive_registry_dry_run() -> None:
    now = datetime.now(timezone.utc)
    task = TaskRequest(
        task_id="actual-hive-contract-1",
        correlation_id="actual-hive-contract-correlation",
        actor="chatgpt:johnny-work",
        capability="diagnostics.synthetic_status.v1",
        target_id="integration-node",
        arguments={},
        requested_at=now,
        expires_at=now + timedelta(minutes=2),
        provenance=Provenance("cybercore", "integration-test", "local", now),
    )
    kernel = ActionKernel(
        targets={"integration-node": {"synthetic_status": "ok"}},
        allowed_actors=frozenset({task.actor}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    approved = kernel.execute(task, trusted_actor=task.actor)
    assert approved.status == "EXECUTED"

    registry = NodeAgentRegistry()
    agent = LocalNodeAgent(NodeDescriptor(id=task.target_id))
    registry.register(agent)
    guard = InMemoryReplayGuard()
    result = run_local_hive_dry_run(
        task,
        trusted_actor=task.actor,
        kernel_receipt=approved,
        registry=registry,
        replay_guard=guard,
    )
    assert result.status == "dry_run"
    assert agent.handled_requests == [task.task_id]

    # Same authorization must not reach dispatch twice.
    try:
        run_local_hive_dry_run(
            task,
            trusted_actor=task.actor,
            kernel_receipt=approved,
            registry=registry,
            replay_guard=guard,
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("Replay was incorrectly accepted")
    assert agent.handled_requests == [task.task_id]


def test_real_hive_rejects_denied_authority_without_dispatch() -> None:
    now = datetime.now(timezone.utc)
    task = TaskRequest(
        task_id="real-hive-denied",
        correlation_id="real-hive-denied-correlation",
        actor="chatgpt:johnny-work",
        capability="diagnostics.synthetic_status.v1",
        target_id="integration-denied-node",
        arguments={},
        requested_at=now,
        expires_at=now + timedelta(minutes=2),
        provenance=Provenance("cybercore", "integration-test", "local", now),
    )
    kernel = ActionKernel(
        targets={task.target_id: {"synthetic_status": "ok"}},
        allowed_actors=frozenset({task.actor}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    denied = kernel.execute(task, trusted_actor="chatgpt:unauthorized")
    assert denied.status == "DENIED"

    registry = NodeAgentRegistry()
    agent = LocalNodeAgent(NodeDescriptor(id=task.target_id))
    registry.register(agent)
    with pytest.raises(PermissionError, match="policy did not allow task"):
        run_local_hive_dry_run(
            task,
            trusted_actor="chatgpt:unauthorized",
            kernel_receipt=denied,
            registry=registry,
            replay_guard=InMemoryReplayGuard(),
        )
    assert agent.handled_requests == []


def test_real_hive_rejects_modified_expiry_without_dispatch() -> None:
    now = datetime.now(timezone.utc)
    task = TaskRequest(
        task_id="real-hive-expiry-mismatch",
        correlation_id="real-hive-expiry-correlation",
        actor="chatgpt:johnny-work",
        capability="diagnostics.synthetic_status.v1",
        target_id="integration-expiry-node",
        arguments={},
        requested_at=now,
        expires_at=now + timedelta(minutes=2),
        provenance=Provenance("cybercore", "integration-test", "local", now),
    )
    kernel = ActionKernel(
        targets={task.target_id: {"synthetic_status": "ok"}},
        allowed_actors=frozenset({task.actor}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    approved = kernel.execute(task, trusted_actor=task.actor)
    assert approved.status == "EXECUTED"

    registry = NodeAgentRegistry()
    agent = LocalNodeAgent(NodeDescriptor(id=task.target_id))
    registry.register(agent)
    modified = replace(task, expires_at=task.expires_at + timedelta(seconds=30))
    with pytest.raises(PermissionError, match="authorization expiry do not match"):
        run_local_hive_dry_run(
            modified,
            trusted_actor=task.actor,
            kernel_receipt=approved,
            registry=registry,
            replay_guard=InMemoryReplayGuard(),
        )
    assert agent.handled_requests == []
