from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import socketserver
import stat
from threading import Thread
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


class RoomBackend(Protocol):
    actor: TrustedActor

    def post_event(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def read_events(self, **kwargs: Any) -> list[Mapping[str, Any]]: ...

    def subscribe_events(self, **kwargs: Any) -> list[Mapping[str, Any]]: ...

    def get_runtime_status(self) -> Mapping[str, Any]: ...


class _IdentityUnixServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path: str, backend: RoomBackend) -> None:
        self.backend = backend
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
            result = _dispatch(server.backend, method, args)
            response = {"ok": True, "result": result}
        except Exception as exc:
            response = {
                "ok": False,
                "error": {
                    "type": type(exc).__name__,
                },
            }
        self.wfile.write(json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n")


def _dispatch(backend: RoomBackend, method: str, args: dict[str, Any]) -> object:
    if method == "identity":
        actor = backend.actor
        return {
            "actor_id": actor.actor_id,
            "actor_type": actor.actor_type,
            "display_name": actor.display_name,
            "authorized_rooms": list(actor.room_ids),
        }
    if method == "post_event":
        return backend.post_event(**args)
    if method == "read_events":
        return backend.read_events(**args)
    if method == "subscribe_events":
        return backend.subscribe_events(**args)
    if method == "runtime_status":
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
        self._servers: list[_IdentityUnixServer] = []
        self._threads: list[Thread] = []

    def start(self) -> None:
        if self._servers:
            return
        for identity in sorted(self.backends):
            path = self.socket_paths[identity]
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                mode = path.stat().st_mode
                if not stat.S_ISSOCK(mode):
                    raise RuntimeError(f"broker path exists and is not a socket: {path}")
                path.unlink()
            server = _IdentityUnixServer(str(path), self.backends[identity])
            os.chmod(path, 0o600)
            thread = Thread(
                target=server.serve_forever,
                name=f"cyberdjs-room-{identity}",
                daemon=True,
            )
            thread.start()
            self._servers.append(server)
            self._threads.append(thread)

    def stop(self) -> None:
        for server in self._servers:
            server.shutdown()
        for server in self._servers:
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._servers.clear()
        self._threads.clear()
        for path in self.socket_paths.values():
            if path.exists() and stat.S_ISSOCK(path.stat().st_mode):
                path.unlink()


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
