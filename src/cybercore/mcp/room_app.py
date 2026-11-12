from __future__ import annotations

from typing import Any, Mapping, Protocol

from mcp.server import MCPServer

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.nextcloud_r1_tool import TOOL_NAME as NEXTCLOUD_R1_HANDLER_NAME
from cybercore.mcp.server import READ_ONLY_ANNOTATIONS, _bounded_text, _invoke

ROOM_SERVER_NAME = "CyberDJs Room"
ROOM_SERVER_VERSION = "0.1.0"
NEXTCLOUD_R1_MCP_TOOL = "cyberdjs.room.nextcloud_r1"


class RoomAppBackend(Protocol):
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


ROOM_TOOLS = (
    "cyberdjs.room.capabilities",
    "cyberdjs.room.identity",
    "cyberdjs.room.post",
    "cyberdjs.room.read",
    "cyberdjs.room.wait",
    "cyberdjs.room.status",
)


def _allowed_backend_tools(communication: RoomAppBackend) -> frozenset[str]:
    return frozenset(getattr(communication, "allowed_tools", frozenset()))


def _invoke_optional_tool(
    communication: RoomAppBackend,
    *,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> Mapping[str, Any]:
    invoke = getattr(communication, "invoke_tool", None)
    if not callable(invoke):
        raise PermissionError("governed backend tool is unavailable")
    result = invoke(tool_name=tool_name, arguments=arguments)
    if not isinstance(result, Mapping):
        raise RuntimeError("governed backend returned a malformed result")
    return result


def room_capability_manifest(
    *,
    actor_id: str,
    wake_enabled: bool,
    governed_tools: tuple[str, ...] = (),
) -> dict[str, object]:
    tools = list(ROOM_TOOLS)
    if NEXTCLOUD_R1_HANDLER_NAME in governed_tools:
        tools.append(NEXTCLOUD_R1_MCP_TOOL)
    return {
        "server": ROOM_SERVER_NAME,
        "version": ROOM_SERVER_VERSION,
        "mode": "shared_cyberhive_room",
        "actor_id": actor_id,
        "tools": tools,
        "governed_backend_tools": list(governed_tools),
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
    allowed_backend_tools = _allowed_backend_tools(communication)

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
                    governed_tools=tuple(sorted(allowed_backend_tools)),
                ),
            },
        )

    @server.tool(name="cyberdjs.room.identity", annotations=READ_ONLY_ANNOTATIONS)
    async def identity() -> dict[str, object]:
        actor = communication.actor
        runtime = dict(communication.get_runtime_status())
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
                    "participant_role": runtime.get("participant_role", "participant"),
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

    if NEXTCLOUD_R1_HANDLER_NAME in allowed_backend_tools:

        @server.tool(name=NEXTCLOUD_R1_MCP_TOOL)
        async def nextcloud_r1(
            action: str,
            operation_id: str,
            plan_id: str,
            plan_revision: str,
            authorization_reference: str,
        ) -> dict[str, object]:
            return await _invoke(
                NEXTCLOUD_R1_MCP_TOOL,
                lambda rid: {
                    "ok": True,
                    "request_id": rid,
                    "execution": dict(
                        _invoke_optional_tool(
                            communication,
                            tool_name=NEXTCLOUD_R1_HANDLER_NAME,
                            arguments={
                                "action": action,
                                "operation_id": operation_id,
                                "plan_id": plan_id,
                                "plan_revision": plan_revision,
                                "authorization_reference": authorization_reference,
                            },
                        )
                    ),
                },
            )

    return server
