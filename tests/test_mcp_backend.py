from cybercore.communication.agent_registry import AgentDescriptor, AgentRegistry
from cybercore.communication.contracts import AgentReply, RoomEvent, TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.mcp.backend import RoomCommunicationBackend


class Echo:
    def respond(self, event):
        return AgentReply(text=f"echo:{event.payload['text']}")


class Gateway:
    def __init__(self):
        self.events = []

    def append(self, draft, *, actor):
        event = RoomEvent(
            event_id=draft.event_id,
            timestamp=draft.timestamp,
            sequence=len(self.events) + 1,
            room_id=draft.room_id,
            session_id=draft.session_id,
            actor_id=draft.actor_id,
            actor_type=draft.actor_type,
            target=draft.target,
            event_type=draft.event_type,
            payload=draft.payload,
            correlation_id=draft.correlation_id,
            causation_id=draft.causation_id,
            metadata=draft.metadata,
        )
        self.events.append(event)
        return event

    def read(self, room_id, session_id, *, actor, after_sequence=0, limit=100):
        return tuple(
            event for event in self.events
            if event.sequence > after_sequence
        )[:limit]


def backend():
    gateway = Gateway()
    agents = AgentRegistry()
    agents.register(AgentDescriptor("agent-a", "Agent A", Echo()))
    coordinator = RoomCoordinator(gateway=gateway, agents=agents)
    actor = TrustedActor(
        "human-1", "human", "Human", ("room-1",), ("session-1",)
    )
    return RoomCommunicationBackend(
        coordinator=coordinator,
        actor=actor,
        presence_getter=lambda room_id, session_id: [
            {"actor_id": "human-1"}
        ],
        runtime_status=lambda: {"state": "ready"},
        tool_handlers={
            "safe.echo": lambda args: {"echo": args}
        },
    )


def test_backend_binds_identity_and_invokes_agent():
    value = backend()
    events = value.invoke_agent(
        room_id="room-1",
        session_id="session-1",
        target_agent="agent-a",
        message="hi",
    )
    assert events[0]["actor_id"] == "human-1"
    assert events[1]["actor_id"] == "agent-a"


def test_backend_tool_allowlist_is_explicit():
    value = backend()
    assert value.allowed_tools == frozenset({"safe.echo"})
    assert value.invoke_tool(
        tool_name="safe.echo", arguments={"x": 1}
    ) == {"echo": {"x": 1}}
    try:
        value.invoke_tool(
            tool_name="unsafe.shell", arguments={}
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "unallowlisted tool did not fail closed"
        )
