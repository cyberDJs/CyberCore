from dataclasses import dataclass

from cybercore.communication.contracts import RoomEventDraft, TrustedActor
from cybercore.cyberhive_runtime import CyberHIVEEventGateway


@dataclass
class FakeContext:
    actor_id: str
    actor_type: str
    room_ids: tuple[str, ...]
    session_ids: tuple[str, ...]


class FakeEvent:
    def __init__(self, **data):
        self.data = data

    def to_dict(self):
        return dict(self.data)


class FakeCommunicationEvent:
    @classmethod
    def draft(cls, **data):
        return FakeEvent(sequence=0, previous_hash=None, event_hash="", **data)


class FakeEventsModule:
    EventAccessContext = FakeContext
    CommunicationEvent = FakeCommunicationEvent


class FakeStore:
    def __init__(self):
        self.last_context = None
        self.last_event = None

    def append(self, event, *, context):
        self.last_context = context
        self.last_event = event
        data = event.to_dict()
        data.update(
            {
                "sequence": 1,
                "previous_hash": None,
                "event_hash": "hash-1",
            }
        )
        return FakeEvent(**data)

    def read(self, room_id, session_id, *, context, after_sequence=0, limit=100):
        self.last_context = context
        return ()


def test_adapter_translates_trusted_actor_and_room_event_without_hive_import():
    store = FakeStore()
    gateway = CyberHIVEEventGateway(store, events_module=FakeEventsModule)
    actor = TrustedActor(
        "human-1",
        "human",
        "Human",
        ("room-1",),
        ("session-1",),
    )
    event = gateway.append(
        RoomEventDraft(
            event_id="evt-1",
            room_id="room-1",
            session_id="session-1",
            actor_id="human-1",
            actor_type="human",
            target="*",
            event_type="message.text",
            payload={"text": "hello"},
        ),
        actor=actor,
    )
    assert store.last_context.actor_id == "human-1"
    assert store.last_context.room_ids == ("room-1",)
    assert event.sequence == 1
    assert event.actor_id == "human-1"
