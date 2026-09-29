import asyncio
import json
from pathlib import Path

from mcp import Client

from cybercore.mcp.server import (
    AVAILABLE_TOOLS,
    build_server,
    capability_manifest,
)


class FakeBackend:
    allowed_tools = frozenset({"safe.echo"})

    def post_event(self, **kwargs):
        return {
            "event_id": "evt-1",
            "actor_id": "trusted-boundary",
        }

    def read_events(self, **kwargs):
        return [{"event_id": "evt-1", "sequence": 1}]

    def subscribe_events(self, **kwargs):
        return []

    def get_presence(self, **kwargs):
        return [{"actor_id": "trusted-boundary"}]

    def get_runtime_status(self):
        return {"state": "ready"}

    def invoke_agent(self, **kwargs):
        return [
            {
                "event_type": "message.text",
                "actor_id": kwargs["target_agent"],
            }
        ]

    def invoke_tool(self, **kwargs):
        return {"echo": kwargs["arguments"]}


async def exercise(repo):
    async with Client(build_server(repo, communication=FakeBackend())) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == set(AVAILABLE_TOOLS)
        caps = await client.call_tool("cybercore.capabilities", {})
        assert caps.structured_content["communication_backend_configured"] is True
        post = await client.call_tool(
            "cybercore.events.post",
            {
                "room_id": "room-1",
                "session_id": "session-1",
                "target": "*",
                "event_type": "message.text",
                "payload_json": json.dumps(
                    {
                        "text": "hello",
                        "token": "secret",
                    }
                ),
            },
        )
        rendered = json.dumps(post.structured_content)
        assert "secret" not in rendered
        denied = await client.call_tool(
            "cybercore.tool.invoke",
            {
                "tool_name": "unsafe.shell",
                "arguments_json": "{}",
            },
        )
        assert denied.structured_content["ok"] is False
        assert denied.structured_content["error"]["code"] == "forbidden"


def test_mcp_protocol_tools_and_governed_backend():
    asyncio.run(exercise(str(Path.cwd())))


def test_manifest_declares_both_transports_and_no_external_mutation():
    manifest = capability_manifest()
    assert manifest["transport"] == [
        "stdio",
        "streamable-http",
    ]
    assert manifest["mutation"]["external_effects"] is False
    assert manifest["mutation"]["approval_bypass"] is False
