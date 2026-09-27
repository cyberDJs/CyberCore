from cybercore.communication.contracts import RoomEvent
from cybercore.wake.dispatcher import WakeDispatcher, WakeRequest
from cybercore.wake.slack import SlackIncomingWebhookWakeSink


class RecordingSink:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)


class FailingSink:
    def send(self, request):
        raise RuntimeError("boom")


def event(
    *,
    actor_id="human-1",
    actor_type="human",
    target="chatgpt:eimy",
    event_type="message.text",
):
    return RoomEvent(
        event_id="evt-1",
        timestamp="2026-09-27T12:00:00+00:00",
        sequence=7,
        room_id="cyberdjs-main",
        session_id="session-1",
        actor_id=actor_id,
        actor_type=actor_type,
        target=target,
        event_type=event_type,
        payload={"text": "private room text that must not enter Slack"},
    )


def test_explicit_target_wakes_only_requested_identity():
    work = RecordingSink()
    moderator = RecordingSink()
    eimy = RecordingSink()
    dispatcher = WakeDispatcher(
        {
            "chatgpt:johnny-work": work,
            "chatgpt:johnny-mod": moderator,
            "chatgpt:eimy": eimy,
        }
    )
    dispatcher.start()
    accepted = dispatcher.submit(event())
    assert [item.target for item in accepted] == ["chatgpt:eimy"]
    assert dispatcher.drain()
    dispatcher.stop()
    assert len(work.requests) == 0
    assert len(moderator.requests) == 0
    assert len(eimy.requests) == 1


def test_broadcast_wakes_all_other_ai_participants():
    work = RecordingSink()
    moderator = RecordingSink()
    eimy = RecordingSink()
    dispatcher = WakeDispatcher(
        {
            "chatgpt:johnny-work": work,
            "chatgpt:johnny-mod": moderator,
            "chatgpt:eimy": eimy,
        }
    )
    dispatcher.start()

    accepted = dispatcher.submit(event(target="*"))
    assert {item.target for item in accepted} == {
        "chatgpt:johnny-work",
        "chatgpt:johnny-mod",
        "chatgpt:eimy",
    }
    assert dispatcher.drain()

    work.requests.clear()
    moderator.requests.clear()
    eimy.requests.clear()
    accepted = dispatcher.submit(
        event(actor_id="chatgpt:johnny-work", actor_type="agent", target="*")
    )
    assert {item.target for item in accepted} == {"chatgpt:johnny-mod", "chatgpt:eimy"}
    assert dispatcher.drain()
    dispatcher.stop()
    assert len(work.requests) == 0
    assert len(moderator.requests) == 1
    assert len(eimy.requests) == 1


def test_delivery_failure_is_best_effort_and_does_not_raise_to_submitter():
    dispatcher = WakeDispatcher({"chatgpt:eimy": FailingSink()})
    dispatcher.start()
    assert len(dispatcher.submit(event())) == 1
    assert dispatcher.drain()
    dispatcher.stop()


def test_slack_payload_contains_locator_only_not_room_message_text():
    rendered = SlackIncomingWebhookWakeSink.render(
        WakeRequest.from_event(event(), target="chatgpt:eimy")
    )
    assert "private room text" not in rendered
    assert "event=evt-1" in rendered
    assert "target=chatgpt:eimy" in rendered
