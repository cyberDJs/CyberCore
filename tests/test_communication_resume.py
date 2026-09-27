from cybercore.communication.agent_registry import AgentRegistry
from cybercore.communication.contracts import RoomEvent, TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator


class ResumeGateway:
    def __init__(self, events):
        self.events = list(events)

    def append(self, draft, *, actor):
        raise AssertionError("resume test is read-only")

    def read(self, room_id, session_id, *, actor, after_sequence=0, limit=100):
        return tuple(
            event for event in self.events
            if event.room_id == room_id
            and event.session_id == session_id
            and event.sequence > after_sequence
        )[:limit]


def test_coordinator_resume_does_not_replay_old_events():
    events = [
        RoomEvent(
            event_id=f"evt-{index}",
            timestamp="2026-09-27T00:00:00+00:00",
            sequence=index,
            room_id="room-1",
            session_id="session-1",
            actor_id="agent-a",
            actor_type="agent",
            target="human-1",
            event_type="message.text",
            payload={"text": str(index)},
        )
        for index in (1, 2, 3)
    ]
    coordinator = RoomCoordinator(
        gateway=ResumeGateway(events), agents=AgentRegistry()
    )
    actor = TrustedActor(
        "human-1", "human", "Human", ("room-1",), ("session-1",)
    )
    resumed = coordinator.resume(
        room_id="room-1", session_id="session-1", actor=actor, after_sequence=2
    )
    assert [event.sequence for event in resumed] == [3]
