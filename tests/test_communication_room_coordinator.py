from hashlib import sha256
import json

from cybercore.communication.agent_registry import AgentDescriptor, AgentRegistry
from cybercore.communication.contracts import RoomEvent, TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.communication.test_agents import EchoAgent, FailingAgent


class MemoryGateway:
    def __init__(self):
        self.events = []

    def append(self, draft, *, actor):
        assert draft.actor_id == actor.actor_id
        assert draft.actor_type == actor.actor_type
        assert draft.room_id in actor.room_ids
        if actor.session_ids:
            assert draft.session_id in actor.session_ids
        seq = len(self.events) + 1
        prev = self.events[-1].event_hash if self.events else None
        raw = {
            "event_id": draft.event_id,
            "sequence": seq,
            "previous_hash": prev,
        }
        digest = sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        event = RoomEvent(
            event_id=draft.event_id,
            timestamp=draft.timestamp,
            sequence=seq,
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
            previous_hash=prev,
            event_hash=digest,
        )
        self.events.append(event)
        return event

    def read(self, room_id, session_id, *, actor, after_sequence=0, limit=100):
        assert room_id in actor.room_ids
        return tuple(
            event
            for event in self.events
            if event.room_id == room_id
            and event.session_id == session_id
            and event.sequence > after_sequence
        )[:limit]


def human():
    return TrustedActor(
        "human-1", "human", "Human", ("room-1",), ("session-1",)
    )


def test_broadcast_reaches_two_agents_in_deterministic_floor_order():
    gateway = MemoryGateway()
    agents = AgentRegistry()
    agents.register(AgentDescriptor("agent-b", "Agent B", EchoAgent("B"), priority=20))
    agents.register(AgentDescriptor("agent-a", "Agent A", EchoAgent("A"), priority=10))
    coordinator = RoomCoordinator(gateway=gateway, agents=agents)
    events = coordinator.submit_text(
        room_id="room-1",
        session_id="session-1",
        actor=human(),
        text="hello",
        event_id="evt-user",
    )
    assert [event.actor_id for event in events] == ["human-1", "agent-a", "agent-b"]
    assert [event.payload["text"] for event in events[1:]] == ["A: hello", "B: hello"]
    assert all(event.correlation_id == "evt-user" for event in events[1:])


def test_offline_agent_is_skipped_and_failure_becomes_system_error():
    gateway = MemoryGateway()
    agents = AgentRegistry()
    agents.register(
        AgentDescriptor("agent-off", "Offline", EchoAgent("OFF"), online=False)
    )
    agents.register(AgentDescriptor("agent-fail", "Fail", FailingAgent()))
    coordinator = RoomCoordinator(gateway=gateway, agents=agents)
    events = coordinator.submit_text(
        room_id="room-1", session_id="session-1", actor=human(), text="hello"
    )
    assert [event.event_type for event in events] == ["message.text", "system.error"]
    assert events[-1].payload["agent_id"] == "agent-fail"


def test_target_specific_routing_and_resume():
    gateway = MemoryGateway()
    agents = AgentRegistry()
    agents.register(AgentDescriptor("agent-a", "Agent A", EchoAgent("A")))
    agents.register(AgentDescriptor("agent-b", "Agent B", EchoAgent("B")))
    coordinator = RoomCoordinator(gateway=gateway, agents=agents)
    events = coordinator.submit_text(
        room_id="room-1",
        session_id="session-1",
        actor=human(),
        text="hello",
        target="agent-b",
    )
    assert [event.actor_id for event in events] == ["human-1", "agent-b"]
    resumed = coordinator.resume(
        room_id="room-1", session_id="session-1", actor=human(), after_sequence=1
    )
    assert [event.actor_id for event in resumed] == ["agent-b"]


def test_voice_transcript_uses_same_session_history():
    gateway = MemoryGateway()
    coordinator = RoomCoordinator(gateway=gateway, agents=AgentRegistry())
    event = coordinator.submit_voice_transcript(
        room_id="room-1",
        session_id="session-1",
        actor=human(),
        transcript="spoken input",
    )
    assert event.event_type == "message.voice.transcript"
    assert (
        coordinator.resume(
            room_id="room-1",
            session_id="session-1",
            actor=human(),
            after_sequence=0,
        )[0].event_id
        == event.event_id
    )
