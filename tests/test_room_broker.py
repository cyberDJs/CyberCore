from __future__ import annotations

from pathlib import Path

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.room_broker import RoomBroker
from cybercore.mcp.room_broker_client import BrokerRoomBackend


class FakeBackend:
    def __init__(self, actor_id: str):
        self.actor = TrustedActor(
            actor_id,
            "agent",
            actor_id,
            ("cyberdjs-main",),
        )
        self.posts = []

    def post_event(self, **kwargs):
        self.posts.append(kwargs)
        return {
            "event_id": "evt-1",
            "sequence": 1,
            "actor_id": self.actor.actor_id,
            **kwargs,
        }

    def read_events(self, **kwargs):
        return []

    def subscribe_events(self, **kwargs):
        return []

    def get_runtime_status(self):
        return {
            "state": "ready",
            "actor_id": self.actor.actor_id,
            "writer_model": "single-broker",
        }


def test_broker_socket_fixes_identity_and_keeps_one_runtime_owner(tmp_path: Path):
    johnny = FakeBackend("chatgpt:johnny")
    eimy = FakeBackend("chatgpt:eimy")
    sockets = {
        "chatgpt:johnny": tmp_path / "johnny.sock",
        "chatgpt:eimy": tmp_path / "eimy.sock",
    }
    broker = RoomBroker(
        {
            "chatgpt:johnny": johnny,
            "chatgpt:eimy": eimy,
        },
        sockets,
    )
    broker.start()
    try:
        johnny_client = BrokerRoomBackend(sockets["chatgpt:johnny"])
        eimy_client = BrokerRoomBackend(sockets["chatgpt:eimy"])

        assert johnny_client.actor.actor_id == "chatgpt:johnny"
        assert eimy_client.actor.actor_id == "chatgpt:eimy"

        posted = johnny_client.post_event(
            room_id="cyberdjs-main",
            session_id="session-1",
            target="chatgpt:eimy",
            event_type="message.text",
            payload={"text": "hello"},
        )
        assert posted["actor_id"] == "chatgpt:johnny"
        assert len(johnny.posts) == 1
        assert len(eimy.posts) == 0
        assert johnny_client.get_runtime_status()["writer_model"] == "single-broker"
    finally:
        broker.stop()


def test_broker_refuses_to_unlink_non_socket_path(tmp_path: Path):
    path = tmp_path / "johnny.sock"
    path.write_text("do not delete")
    broker = RoomBroker(
        {"chatgpt:johnny": FakeBackend("chatgpt:johnny")},
        {"chatgpt:johnny": path},
    )
    try:
        broker.start()
    except RuntimeError as exc:
        assert "not a socket" in str(exc)
    else:
        raise AssertionError("broker should reject a non-socket path")
    assert path.read_text() == "do not delete"
