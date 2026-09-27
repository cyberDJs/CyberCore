import pytest

from cybercore.communication.agent_registry import AgentDescriptor, AgentRegistry
from cybercore.communication.test_agents import EchoAgent


def test_registry_rejects_duplicate_identity():
    registry = AgentRegistry()
    descriptor = AgentDescriptor("agent-a", "Agent A", EchoAgent("A"))
    registry.register(descriptor)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(descriptor)


def test_selection_skips_offline_and_is_priority_ordered():
    registry = AgentRegistry()
    registry.register(AgentDescriptor("agent-b", "B", EchoAgent("B"), priority=20))
    registry.register(AgentDescriptor("agent-a", "A", EchoAgent("A"), priority=10))
    registry.register(AgentDescriptor("agent-off", "Off", EchoAgent("O"), online=False))
    assert [item.actor_id for item in registry.select("*")] == ["agent-a", "agent-b"]
