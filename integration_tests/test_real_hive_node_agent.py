"""Integration smoke test using real pinned CyberHIVE classes (not mock types)."""

from datetime import datetime, timedelta, timezone

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
