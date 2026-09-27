from __future__ import annotations

from typing import Any, Mapping, Protocol

from mcp.server import MCPServer

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.server import READ_ONLY_ANNOTATIONS, _bounded_text, _invoke

ROOM_SERVER_NAME = "CyberDJs Room"
ROOM_SERVER_VERSION = "0.1.0"
class RoomAppBackend(Protocol):
    actor: TrustedActor

    def post_event(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def read_events(self, **kwargs: Any) -> list[Mapping[str, Any]]: ...

    def subscribe_events(self, **kwargs: Any) -> list[Mapping[str, Any]]: ...

    def get_runtime_status(self) -> Mapping[str, Any]: ...


ROOM_TOOLS = (
    "cyberdjs.room.capabilities",
    "cyberdjs.room.identity",
    "cyberdjs.room.post",
    "cyberdjs.room.read",
    "cyberdjs.room.wait",
    "cyberdjs.room.status",
)


def room_capability_manifest(*, actor_id: str, wake_enabled: bool) -> dict[str, object]:
    return {
        "server": ROOM_SERVER_NAME,
        "version": ROOM_SERVER_VERSION,
        "mode": "shared_cyberhive_room",
        "actor_id": actor_id,
        "tools": list(ROOM_TOOLS),
        "wake": {
            "event_driven": True,
            "slack_adapter_enabled": wake_enabled,
            "polling": False,
        },
    }


def build_room_app_server(
    communication: RoomAppBackend,
    *,
    wake_enabled: bool = False,
) -> MCPServer:
    server = MCPServer(ROOM_SERVER_NAME)

    @server.tool(name="cyberdjs.room.capabilities", annotations=READ_ONLY_ANNOTATIONS)
    async def capabilities() -> dict[str, object]:
        return await _invoke(
            "cyberdjs.room.capabilities",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                **room_capability_manifest(
                    actor_id=communication.actor.actor_id,
                    wake_enabled=wake_enabled,
                ),
            },
        )

    @server.tool(name="cyberdjs.room.identity", annotations=READ_ONLY_ANNOTATIONS)
    async def identity() -> dict[str, object]:
        actor = communication.actor
        return await _invoke(
            "cyberdjs.room.identity",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "identity": {
                    "actor_id": actor.actor_id,
                    "actor_type": actor.actor_type,
                    "display_name": actor.display_name,
                    "authorized_rooms": list(actor.room_ids),
                },
            },
        )

    @server.tool(name="cyberdjs.room.post")
    async def post(room_id: str, session_id: str, target: str, text: str) -> dict[str, object]:
        return await _invoke(
            "cyberdjs.room.post",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "event": communication.post_event(
                    room_id=room_id,
                    session_id=session_id,
                    target=target,
                    event_type="message.text",
                    payload={"text": _bounded_text(text, name="text")},
                ),
            },
        )

    @server.tool(name="cyberdjs.room.read", annotations=READ_ONLY_ANNOTATIONS)
    async def read(
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> dict[str, object]:
        return await _invoke(
            "cyberdjs.room.read",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "events": communication.read_events(
                    room_id=room_id,
                    session_id=session_id,
                    after_sequence=after_sequence,
                    limit=limit,
                ),
            },
        )

    @server.tool(name="cyberdjs.room.wait", annotations=READ_ONLY_ANNOTATIONS)
    async def wait(
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
        wait_seconds: float = 1.0,
    ) -> dict[str, object]:
        return await _invoke(
            "cyberdjs.room.wait",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "mode": "bounded_long_poll_active_session_only",
                "events": communication.subscribe_events(
                    room_id=room_id,
                    session_id=session_id,
                    after_sequence=after_sequence,
                    limit=limit,
                    wait_seconds=wait_seconds,
                ),
            },
        )

    @server.tool(name="cyberdjs.room.status", annotations=READ_ONLY_ANNOTATIONS)
    async def status() -> dict[str, object]:
        return await _invoke(
            "cyberdjs.room.status",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "runtime": dict(communication.get_runtime_status()),
            },
        )

    return server
