from __future__ import annotations

from pathlib import Path
import threading
import time

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.room_broker import RoomBroker
from cybercore.mcp.room_broker_client import BrokerRoomBackend


class ConcurrencyTracker:
    def __init__(self):
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()


class FakeBackend:
    def __init__(self, actor_id: str, tracker: ConcurrencyTracker | None = None):
        self.actor = TrustedActor(
            actor_id,
            "agent",
            actor_id,
            ("cyberdjs-main",),
        )
        self.posts = []
        self.tracker = tracker

    def post_event(self, **kwargs):
        if self.tracker is not None:
            with self.tracker.lock:
                self.tracker.active += 1
                self.tracker.max_active = max(self.tracker.max_active, self.tracker.active)
        try:
            time.sleep(0.01)
            self.posts.append(kwargs)
            return {
                "event_id": f"evt-{len(self.posts)}",
                "sequence": len(self.posts),
                "actor_id": self.actor.actor_id,
                **kwargs,
            }
        finally:
            if self.tracker is not None:
                with self.tracker.lock:
                    self.tracker.active -= 1

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


def test_broker_serializes_concurrent_posts_across_identity_sockets(tmp_path: Path):
    tracker = ConcurrencyTracker()
    shared = FakeBackend("chatgpt:johnny", tracker)
    other = FakeBackend("chatgpt:eimy", tracker)
    sockets = {
        "chatgpt:johnny": tmp_path / "johnny.sock",
        "chatgpt:eimy": tmp_path / "eimy.sock",
    }
    broker = RoomBroker(
        {
            "chatgpt:johnny": shared,
            "chatgpt:eimy": other,
        },
        sockets,
    )
    broker.start()
    try:
        johnny_client = BrokerRoomBackend(sockets["chatgpt:johnny"])
        eimy_client = BrokerRoomBackend(sockets["chatgpt:eimy"])

        errors = []

        def post(client, target):
            try:
                client.post_event(
                    room_id="cyberdjs-main",
                    session_id="session-1",
                    target=target,
                    event_type="message.text",
                    payload={"text": "concurrent"},
                )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=post, args=(johnny_client, "chatgpt:eimy")),
            threading.Thread(target=post, args=(eimy_client, "chatgpt:johnny")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert errors == []
        assert tracker.max_active == 1
    finally:
        broker.stop()


def test_broker_rejects_second_live_broker_without_replacing_socket(tmp_path: Path):
    path = tmp_path / "johnny.sock"
    first = RoomBroker(
        {"chatgpt:johnny": FakeBackend("chatgpt:johnny")},
        {"chatgpt:johnny": path},
    )
    second = RoomBroker(
        {"chatgpt:johnny": FakeBackend("chatgpt:johnny")},
        {"chatgpt:johnny": path},
    )
    first.start()
    try:
        original = BrokerRoomBackend(path)
        assert original.actor.actor_id == "chatgpt:johnny"
        try:
            second.start()
        except RuntimeError as exc:
            assert "already active" in str(exc)
        else:
            raise AssertionError("second live broker must be rejected")

        still_original = BrokerRoomBackend(path)
        assert still_original.actor.actor_id == "chatgpt:johnny"
    finally:
        second.stop()
        first.stop()


def test_long_poll_has_transport_timeout_headroom(tmp_path: Path):
    path = tmp_path / "johnny.sock"
    broker = RoomBroker(
        {"chatgpt:johnny": FakeBackend("chatgpt:johnny")},
        {"chatgpt:johnny": path},
    )
    broker.start()
    try:
        client = BrokerRoomBackend(path, timeout_seconds=0.05)
        started = time.monotonic()
        events = client.subscribe_events(
            room_id="cyberdjs-main",
            session_id="session-1",
            wait_seconds=0.2,
        )
        elapsed = time.monotonic() - started
        assert events == []
        assert elapsed >= 0.18
    finally:
        broker.stop()
