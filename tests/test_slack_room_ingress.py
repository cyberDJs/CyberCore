from __future__ import annotations

from pathlib import Path

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.room_broker import RoomBroker
from cybercore.mcp.slack_ingress import SlackIngressMessage, SlackRoomIngress


class FakeBackend:
    def __init__(self, actor_id: str):
        self.actor = TrustedActor(actor_id, "agent", actor_id, ("cyberdjs-main",))
        self.posts: list[dict] = []

    def post_event(self, **kwargs):
        event = {
            "event_id": f"evt-{len(self.posts) + 1}",
            "sequence": len(self.posts) + 1,
            "actor_id": self.actor.actor_id,
            **kwargs,
        }
        self.posts.append(event)
        return event

    def read_events(self, **kwargs):
        session_id = kwargs["session_id"]
        after_sequence = kwargs.get("after_sequence", 0)
        return [
            event
            for event in self.posts
            if event["session_id"] == session_id and event["sequence"] > after_sequence
        ]

    def subscribe_events(self, **kwargs):
        return self.read_events(**kwargs)

    def get_runtime_status(self):
        return {"state": "ready", "actor_id": self.actor.actor_id}


def _runtime(tmp_path: Path):
    eimy = FakeBackend("chatgpt:eimy")
    moderator = FakeBackend("chatgpt:johnny-mod")
    sockets = {
        "chatgpt:eimy": tmp_path / "eimy.sock",
        "chatgpt:johnny-mod": tmp_path / "johnny-mod.sock",
    }
    broker = RoomBroker(
        {"chatgpt:eimy": eimy, "chatgpt:johnny-mod": moderator},
        sockets,
    )
    broker.start()
    ingress = SlackRoomIngress(
        room_id="cyberdjs-main",
        channel_id="CROOM",
        user_map={"UEIMY": "chatgpt:eimy", "UJOHNNY": "chatgpt:johnny-mod"},
        socket_dir=tmp_path,
    )
    return broker, ingress, eimy, moderator


def test_slack_message_maps_to_server_bound_eimy_identity(tmp_path: Path):
    broker, ingress, eimy, moderator = _runtime(tmp_path)
    try:
        result = ingress.ingest(
            SlackIngressMessage(
                channel_id="CROOM",
                message_ts="100.001",
                user_id="UEIMY",
                text="hello from plus",
            )
        )
        assert result is not None
        assert result["actor_id"] == "chatgpt:eimy"
        assert result["target"] == "*"
        assert result["session_id"] == "slack-CROOM"
        assert result["payload"]["transport"] == "slack"
        assert result["payload"]["slack_message_ts"] == "100.001"
        assert len(eimy.posts) == 1
        assert moderator.posts == []
    finally:
        broker.stop()


def test_same_slack_message_is_idempotent_by_channel_and_timestamp(tmp_path: Path):
    broker, ingress, eimy, _ = _runtime(tmp_path)
    message = SlackIngressMessage(
        channel_id="CROOM",
        message_ts="100.002",
        user_id="UEIMY",
        text="only once",
    )
    try:
        assert ingress.ingest(message) is not None
        assert ingress.ingest(message) is None
        assert len(eimy.posts) == 1
    finally:
        broker.stop()


def test_unknown_slack_user_fails_closed_without_room_write(tmp_path: Path):
    broker, ingress, eimy, moderator = _runtime(tmp_path)
    try:
        result = ingress.ingest(
            SlackIngressMessage(
                channel_id="CROOM",
                message_ts="100.003",
                user_id="UUNKNOWN",
                text="no mapping",
            )
        )
        assert result is None
        assert eimy.posts == []
        assert moderator.posts == []
    finally:
        broker.stop()


def test_system_and_bot_messages_are_ignored():
    assert SlackIngressMessage.from_slack(
        "CROOM", {"ts": "1", "user": "UEIMY", "text": "joined", "subtype": "channel_join"}
    ) is None
    assert SlackIngressMessage.from_slack(
        "CROOM", {"ts": "2", "user": "UBOT", "text": "wake", "subtype": "bot_message"}
    ) is None


def test_ingest_many_processes_oldest_first(tmp_path: Path):
    broker, ingress, eimy, _ = _runtime(tmp_path)
    try:
        count, max_ts = ingress.ingest_many(
            [
                {"ts": "200.002", "user": "UEIMY", "text": "second"},
                {"ts": "200.001", "user": "UEIMY", "text": "first"},
            ]
        )
        assert count == 2
        assert max_ts == "200.002"
        assert [item["payload"]["text"] for item in eimy.posts] == ["first", "second"]
    finally:
        broker.stop()
