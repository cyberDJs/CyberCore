from cybercore.communication.contracts import RoomEvent, RoomEventDraft, TrustedActor
from cybercore.wake.dispatcher import WakeDispatcher
from cybercore.wake.gateway import WakeAwareEventGateway


class RecordingSink:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)


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
        )
        self.events.append(event)
        return event

    def read(self, room_id, session_id, *, actor, after_sequence=0, limit=100):
        return tuple(self.events)


def test_wake_happens_only_after_delegate_persisted_the_event():
    sink = RecordingSink()
    dispatcher = WakeDispatcher({"chatgpt:eimy": sink})
    dispatcher.start()
    delegate = Gateway()
    gateway = WakeAwareEventGateway(delegate, dispatcher)
    actor = TrustedActor("human-1", "human", "Human", ("cyberdjs-main",))
    gateway.append(
        RoomEventDraft(
            event_id="evt-1",
            room_id="cyberdjs-main",
            session_id="session-1",
            actor_id="human-1",
            actor_type="human",
            target="chatgpt:eimy",
            event_type="message.text",
            payload={"text": "hello"},
        ),
        actor=actor,
    )
    assert delegate.events[0].sequence == 1
    assert dispatcher.drain()
    dispatcher.stop()
    assert sink.requests[0].sequence == 1
