from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import sys

import pytest

from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_hive_bridge import run_local_hive_dry_run


def setup():
    now = datetime.now(timezone.utc)
    task = TaskRequest(
        task_id="hive-test-1",
        correlation_id="corr-hive-1",
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


def test_rejects_denied_task_without_dispatch() -> None:
    task, kernel = setup()
    denied = kernel.execute(task, trusted_actor="chatgpt:intruder")
    with pytest.raises(PermissionError):
        run_local_hive_dry_run(
            task,
            trusted_actor="chatgpt:intruder",
            kernel_receipt=denied,
            registry=None,
        )


def test_rejects_receipt_replay_between_tasks() -> None:
    task, kernel = setup()
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
    task, kernel = setup()
    allowed = kernel.execute(task, trusted_actor=task.actor)

    from enum import Enum

    class Action(Enum):
        HEALTH_CHECK = "health_check"

    class Request:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "cyberhive_core",
        SimpleNamespace(),
    )
    monkeypatch.setitem(
        sys.modules,
        "cyberhive_core.node_agent",
        SimpleNamespace(AgentActionRequest=Request, AgentActionType=Action),
    )

    class Registry:
        def dispatch(self, incoming):
            assert incoming.dry_run is True
            assert incoming.action is Action.HEALTH_CHECK
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
    )
    assert receipt.status == "dry_run"
    assert receipt.reason == "HIVE_DRY_RUN_ONLY"
