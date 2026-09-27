import asyncio

from mcp import Client

from cybercore.communication.contracts import TrustedActor
from cybercore.mcp.room_app import ROOM_TOOLS, build_room_app_server


class FakeRoomBackend:
    def __init__(self):
        self.actor = TrustedActor(
            "chatgpt:johnny-work",
            "agent",
            "Johnny Work AI",
            ("cyberdjs-main",),
        )

    def post_event(self, **kwargs):
        return {
            "event_id": "evt-1",
            "actor_id": self.actor.actor_id,
            "actor_type": self.actor.actor_type,
            "room_id": kwargs["room_id"],
            "session_id": kwargs["session_id"],
            "target": kwargs["target"],
            "event_type": kwargs["event_type"],
            "payload": kwargs["payload"],
        }

    def read_events(self, **kwargs):
        return [{"event_id": "evt-1", "sequence": 1, "actor_id": "chatgpt:eimy"}]

    def subscribe_events(self, **kwargs):
        return []

    def get_runtime_status(self):
        return {
            "state": "ready",
            "ledger_integrity": True,
            "participant_role": "participant",
        }


async def exercise_room_app():
    backend = FakeRoomBackend()
    async with Client(build_room_app_server(backend, wake_enabled=True)) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == set(ROOM_TOOLS)

        identity = await client.call_tool("cyberdjs.room.identity", {})
        assert identity.structured_content["identity"]["actor_id"] == "chatgpt:johnny-work"
        assert identity.structured_content["identity"]["participant_role"] == "participant"

        post = await client.call_tool(
            "cyberdjs.room.post",
            {
                "room_id": "cyberdjs-main",
                "session_id": "session-1",
                "target": "chatgpt:eimy",
                "text": "hello",
            },
        )
        assert post.structured_content["event"]["actor_id"] == "chatgpt:johnny-work"
        assert post.structured_content["event"]["target"] == "chatgpt:eimy"

        caps = await client.call_tool("cyberdjs.room.capabilities", {})
        assert caps.structured_content["wake"]["event_driven"] is True
        assert caps.structured_content["wake"]["polling"] is False


def test_room_app_protocol_and_identity_boundary():
    asyncio.run(exercise_room_app())
