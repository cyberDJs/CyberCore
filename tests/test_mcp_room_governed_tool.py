from __future__ import annotations

import asyncio
import json

from mcp import Client

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.nextcloud_r1_tool import TOOL_NAME as NEXTCLOUD_R1_HANDLER_NAME
from cybercore.mcp.room_app import NEXTCLOUD_R1_MCP_TOOL, ROOM_TOOLS, build_room_app_server


class GovernedBackend:
    def __init__(self, *, enabled: bool) -> None:
        self.actor = TrustedActor(
            "chatgpt:johnny-work",
            "agent",
            "Johnny Work AI",
            ("cyberdjs-main",),
        )
        self.allowed_tools = (
            frozenset({NEXTCLOUD_R1_HANDLER_NAME}) if enabled else frozenset()
        )
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post_event(self, **kwargs):
        return {"event_id": "evt-1", **kwargs}

    def read_events(self, **kwargs):
        return []

    def subscribe_events(self, **kwargs):
        return []

    def get_runtime_status(self):
        return {"state": "ready", "participant_role": "participant"}

    def invoke_tool(self, *, tool_name, arguments):
        self.calls.append((tool_name, dict(arguments)))
        return {
            "status": "EXECUTED",
            "authorization_reference_sha256": "0" * 64,
            "secret_values_recorded": False,
        }


async def _listed_tools(backend: GovernedBackend) -> set[str]:
    async with Client(build_room_app_server(backend)) as client:
        listed = await client.list_tools()
        return {tool.name for tool in listed.tools}


def test_governed_tool_is_absent_without_explicit_backend_handler() -> None:
    backend = GovernedBackend(enabled=False)
    assert asyncio.run(_listed_tools(backend)) == set(ROOM_TOOLS)


async def _exercise_enabled() -> None:
    backend = GovernedBackend(enabled=True)
    async with Client(build_room_app_server(backend)) as client:
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == set(ROOM_TOOLS) | {NEXTCLOUD_R1_MCP_TOOL}

        result = await client.call_tool(
            NEXTCLOUD_R1_MCP_TOOL,
            {
                "action": "status",
                "operation_id": "ISSUE-113-R1",
                "plan_id": "GH-113",
                "plan_revision": "1",
                "authorization_reference": "APPROVE-ISSUE-113",
            },
        )
        assert result.structured_content["execution"]["status"] == "EXECUTED"
        assert len(backend.calls) == 1
        tool_name, arguments = backend.calls[0]
        assert tool_name == NEXTCLOUD_R1_HANDLER_NAME
        assert set(arguments) == {
            "action",
            "operation_id",
            "plan_id",
            "plan_revision",
            "authorization_reference",
        }
        assert "host" not in arguments
        assert "path" not in arguments
        assert "command" not in arguments
        assert "APPROVE-ISSUE-113" not in json.dumps(result.structured_content)


def test_governed_tool_is_exposed_only_when_backend_explicitly_allows_it() -> None:
    asyncio.run(_exercise_enabled())
