from hashlib import sha256
import json

import pytest

from cybercore.communication.agent_registry import AgentDescriptor, AgentRegistry
from cybercore.communication.contracts import RoomEvent
from cybercore.communication.http_runtime import build_http_server, handle_room_message
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.communication.test_agents import EchoAgent


class MemoryGateway:
    def __init__(self):
        self.events = []

    def append(self, draft, *, actor):
        assert draft.actor_id == actor.actor_id
        sequence = len(self.events) + 1
        previous_hash = self.events[-1].event_hash if self.events else None
        digest = sha256(
            json.dumps(
                {
                    "event_id": draft.event_id,
                    "sequence": sequence,
                    "previous_hash": previous_hash,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        event = RoomEvent(
            event_id=draft.event_id,
            timestamp=draft.timestamp,
            sequence=sequence,
            room_id=draft.room_id,
            session_id=draft.session_id,
            actor_id=draft.actor_id,
            actor_type=draft.actor_type,
            target=draft.target,
            event_type=draft.event_type,
            payload=draft.payload,
            correlation_id=draft.correlation_id,
            causation_id=draft.causation_id,
            metadata=draft.metadata,
            previous_hash=previous_hash,
            event_hash=digest,
        )
        self.events.append(event)
        return event

    def read(self, room_id, session_id, *, actor, after_sequence=0, limit=100):
        return tuple(
            event
            for event in self.events
            if event.room_id == room_id
            and event.session_id == session_id
            and event.sequence > after_sequence
        )[:limit]


def coordinator():
    agents = AgentRegistry()
    agents.register(AgentDescriptor("agent-a", "Agent A", EchoAgent("A")))
    return RoomCoordinator(gateway=MemoryGateway(), agents=agents)


def test_http_mapping_derives_actor_from_trusted_user_header_context():
    result = handle_room_message(
        coordinator(),
        user_id="user-42",
        payload={
            "room_id": "room-1",
            "session_id": "session-1",
            "text": "hello",
            "target": "*",
            "actor_id": "spoofed-admin",
        },
    )
    assert result["last_sequence"] == 2
    assert result["replies"][0]["actor_id"] == "agent-a"


def test_http_mapping_requires_trusted_user_identity():
    with pytest.raises(PermissionError, match="trusted Open WebUI"):
        handle_room_message(
            coordinator(),
            user_id=None,
            payload={
                "room_id": "room-1",
                "session_id": "session-1",
                "text": "hello",
            },
        )


def test_http_server_rejects_non_loopback_binding():
    with pytest.raises(ValueError, match="non-loopback"):
        build_http_server(coordinator(), host="0.0.0.0", port=0)
