from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import socket
import socketserver
import stat
import time
from threading import RLock, Thread
from typing import Any, Mapping, Protocol, cast

from cybercore.communication.contracts import TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.cyberhive_runtime import LocalMultiAgentRuntime, build_local_runtime
from cybercore.mcp.backend import RoomCommunicationBackend
from cybercore.wake.dispatcher import WakeDispatcher
from cybercore.wake.gateway import WakeAwareEventGateway
from cybercore.wake.slack import SlackIncomingWebhookWakeSink

ALLOWED_CHATGPT_IDENTITIES = frozenset({"chatgpt:johnny", "chatgpt:eimy"})
DEFAULT_DISPLAY_NAMES = {
    "chatgpt:johnny": "Johnny AI",
    "chatgpt:eimy": "Eimy AI",
}
DEFAULT_SOCKET_NAMES = {
    "chatgpt:johnny": "johnny.sock",
    "chatgpt:eimy": "eimy.sock",
}
_MAX_REQUEST_BYTES = 64 * 1024


def _socket_has_live_listener(path: Path) -> bool:
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(0.2)
    try:
        probe.connect(str(path))
    except (ConnectionRefusedError, FileNotFoundError):
        return False
    except OSError:
        raise
    else:
        return True
    finally:
        probe.close()


class RoomBackend(Protocol):
    actor: TrustedActor

    def post_event(
        self,
        *,
        room_id: str,
        session_id: str,
        target: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]: ...

    def read_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[dict[str, Any]]: ...

    def subscribe_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int,
        limit: int,
        wait_seconds: float,
    ) -> list[dict[str, Any]]: ...

    def get_runtime_status(self) -> Mapping[str, Any]: ...


class _IdentityUnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path: str, backend: RoomBackend, ledger_lock: RLock) -> None:
        self.backend = backend
        self.ledger_lock = ledger_lock
        super().__init__(socket_path, _RoomRequestHandler)


class _RoomRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server = cast(_IdentityUnixServer, self.server)
        line = self.rfile.readline(_MAX_REQUEST_BYTES + 1)
        if not line or len(line) > _MAX_REQUEST_BYTES:
            return
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            method = request.get("method")
            args = request.get("args") or {}
            if not isinstance(method, str) or not isinstance(args, dict):
                raise ValueError("invalid broker request")
            result = _dispatch(server.backend, method, args, server.ledger_lock)
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                },
            }
        self.wfile.write(json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n")


def _dispatch(
    backend: RoomBackend,
    method: str,
    args: dict[str, Any],
    ledger_lock: RLock,
) -> object:
    if method == "identity":
        actor = backend.actor
        return {
            "actor_id": actor.actor_id,
            "actor_type": actor.actor_type,
            "display_name": actor.display_name,
            "authorized_rooms": list(actor.room_ids),
        }
    if method == "post_event":
        with ledger_lock:
            return backend.post_event(**args)
    if method == "read_events":
        with ledger_lock:
            return backend.read_events(**args)
    if method == "subscribe_events":
        deadline = time.monotonic() + max(
            0.0,
            min(float(args.get("wait_seconds", 1.0)), 5.0),
        )
        read_args = {
            "room_id": args["room_id"],
            "session_id": args["session_id"],
            "after_sequence": args.get("after_sequence", 0),
            "limit": args.get("limit", 100),
        }
        while True:
            with ledger_lock:
                events = backend.read_events(**read_args)
            if events or time.monotonic() >= deadline:
                return events
            time.sleep(0.1)
    if method == "runtime_status":
        with ledger_lock:
            return dict(backend.get_runtime_status())
    raise ValueError("unsupported broker method")


class RoomBroker:
    """Single-writer broker exposing one identity-bound Unix socket per ChatGPT participant."""

    def __init__(
        self,
        backends: Mapping[str, RoomBackend],
        socket_paths: Mapping[str, str | Path],
    ) -> None:
        if set(backends) != set(socket_paths):
            raise ValueError("broker backends and socket paths must have identical identities")
        self.backends = dict(backends)
        self.socket_paths = {key: Path(value) for key, value in socket_paths.items()}
        parents = {path.parent.resolve() for path in self.socket_paths.values()}
        if len(parents) != 1:
            raise ValueError("all broker sockets must share one directory")
        self._socket_dir = parents.pop()
        self._process_lock_path = self._socket_dir / ".broker.lock"
        self._process_lock_handle: Any | None = None
        self._servers: list[_IdentityUnixServer] = []
        self._threads: list[Thread] = []
        self._owned_socket_paths: set[Path] = set()
        self._ledger_lock = RLock()

    def start(self) -> None:
        if self._servers:
            return

        self._socket_dir.mkdir(parents=True, exist_ok=True)
        lock_handle = self._process_lock_path.open("a+b")
        os.chmod(self._process_lock_path, 0o600)
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock_handle.close()
            raise RuntimeError("another CyberDJs Room broker is already active") from exc
        self._process_lock_handle = lock_handle

        try:
            for identity in sorted(self.backends):
                path = self.socket_paths[identity]
                if path.exists():
                    mode = path.stat().st_mode
                    if not stat.S_ISSOCK(mode):
                        raise RuntimeError(f"broker path exists and is not a socket: {path}")
                    if _socket_has_live_listener(path):
                        raise RuntimeError(f"broker socket already has a live listener: {path}")
                    path.unlink()
                server = _IdentityUnixServer(
                    str(path),
                    self.backends[identity],
                    self._ledger_lock,
                )
                os.chmod(path, 0o600)
                thread = Thread(
                    target=server.serve_forever,
                    name=f"cyberdjs-room-{identity}",
                    daemon=True,
                )
                thread.start()
                self._servers.append(server)
                self._threads.append(thread)
                self._owned_socket_paths.add(path)
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        for server in self._servers:
            server.shutdown()
        for server in self._servers:
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._servers.clear()
        self._threads.clear()
        for path in tuple(self._owned_socket_paths):
            if path.exists() and stat.S_ISSOCK(path.stat().st_mode):
                path.unlink()
        self._owned_socket_paths.clear()
        if self._process_lock_handle is not None:
            fcntl.flock(self._process_lock_handle.fileno(), fcntl.LOCK_UN)
            self._process_lock_handle.close()
            self._process_lock_handle = None


@dataclass(slots=True)
class CyberDJSRoomBrokerRuntime:
    broker: RoomBroker
    dispatcher: WakeDispatcher
    local_runtime: LocalMultiAgentRuntime

    def start(self) -> None:
        self.dispatcher.start()
        self.broker.start()

    def close(self) -> None:
        self.broker.stop()
        self.dispatcher.drain(timeout_seconds=2.0)
        self.dispatcher.stop(timeout_seconds=2.0)


def build_cyberdjs_room_broker_runtime(
    log_path: str | Path,
    *,
    socket_dir: str | Path,
    room_id: str = "cyberdjs-main",
    slack_webhook_url: str | None = None,
) -> CyberDJSRoomBrokerRuntime:
    room_id = room_id.strip()
    if not room_id:
        raise ValueError("room_id must not be empty")

    base = build_local_runtime(log_path)
    sinks: dict[str, Any] = {}
    if slack_webhook_url:
        sink = SlackIncomingWebhookWakeSink(slack_webhook_url)
        sinks = {identity: sink for identity in ALLOWED_CHATGPT_IDENTITIES}

    dispatcher = WakeDispatcher(sinks)
    gateway = WakeAwareEventGateway(base.coordinator.gateway, dispatcher)
    coordinator = RoomCoordinator(gateway=gateway, agents=base.coordinator.agents)

    backends: dict[str, RoomCommunicationBackend] = {}
    for identity in sorted(ALLOWED_CHATGPT_IDENTITIES):
        actor = TrustedActor(
            actor_id=identity,
            actor_type="agent",
            display_name=DEFAULT_DISPLAY_NAMES[identity],
            room_ids=(room_id,),
        )

        def runtime_status(
            *,
            actor: TrustedActor = actor,
        ) -> dict[str, object]:
            return {
                "state": "ready",
                "actor_id": actor.actor_id,
                "room_id": room_id,
                "last_sequence": base.event_store.last_sequence,
                "ledger_integrity": base.event_store.verify_integrity(),
                "wake_enabled": bool(sinks),
                "writer_model": "single-broker",
            }

        backends[identity] = RoomCommunicationBackend(
            coordinator=coordinator,
            actor=actor,
            runtime_status=runtime_status,
        )

    socket_root = Path(socket_dir)
    socket_paths = {
        identity: socket_root / DEFAULT_SOCKET_NAMES[identity]
        for identity in ALLOWED_CHATGPT_IDENTITIES
    }
    return CyberDJSRoomBrokerRuntime(
        broker=RoomBroker(backends, socket_paths),
        dispatcher=dispatcher,
        local_runtime=base,
    )
