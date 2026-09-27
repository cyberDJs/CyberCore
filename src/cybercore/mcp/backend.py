from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

from cybercore.communication.contracts import RoomEventDraft, TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator


class RoomCommunicationBackend:
    """Identity-bound adapter used by MCP transport tools.

    The backend is constructed with a trusted actor by the runtime composition layer.
    Model-supplied arguments never choose actor_id or actor_type.
    """

    def __init__(
        self,
        *,
        coordinator: RoomCoordinator,
        actor: TrustedActor,
        presence_getter: Callable[[str, str], list[dict[str, Any]]] | None = None,
        runtime_status: Callable[[], Mapping[str, Any]] | None = None,
        tool_handlers: Mapping[
            str, Callable[[Mapping[str, Any]], Mapping[str, Any]]
        ] | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.actor = actor
        self.presence_getter = presence_getter
        self.runtime_status_provider = runtime_status
        self.tool_handlers = dict(tool_handlers or {})

    @property
    def allowed_tools(self) -> frozenset[str]:
        return frozenset(self.tool_handlers)

    def post_event(
        self,
        *,
        room_id: str,
        session_id: str,
        target: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        event = self.coordinator.gateway.append(
            RoomEventDraft(
                event_id=f"mcp_{time.time_ns()}",
                room_id=room_id,
                session_id=session_id,
                actor_id=self.actor.actor_id,
                actor_type=self.actor.actor_type,
                target=target,
                event_type=event_type,
                payload=payload,
            ),
            actor=self.actor,
        )
        return {
            name: getattr(event, name)
            for name in event.__dataclass_fields__
        }

    def read_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        events = self.coordinator.resume(
            room_id=room_id,
            session_id=session_id,
            actor=self.actor,
            after_sequence=after_sequence,
            limit=limit,
        )
        return [
            {name: getattr(event, name) for name in event.__dataclass_fields__}
            for event in events
        ]

    def subscribe_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int,
        limit: int,
        wait_seconds: float,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + max(0.0, min(wait_seconds, 5.0))
        while True:
            events = self.read_events(
                room_id=room_id,
                session_id=session_id,
                after_sequence=after_sequence,
                limit=limit,
            )
            if events or time.monotonic() >= deadline:
                return events
            time.sleep(0.1)

    def get_presence(
        self, *, room_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        if self.presence_getter is None:
            raise RuntimeError("presence backend is not configured")
        return self.presence_getter(room_id, session_id)

    def get_runtime_status(self) -> Mapping[str, Any]:
        if self.runtime_status_provider is None:
            raise RuntimeError("runtime status backend is not configured")
        return self.runtime_status_provider()

    def invoke_agent(
        self,
        *,
        room_id: str,
        session_id: str,
        target_agent: str,
        message: str,
    ) -> list[dict[str, Any]]:
        events = self.coordinator.submit_text(
            room_id=room_id,
            session_id=session_id,
            actor=self.actor,
            text=message,
            target=target_agent,
        )
        return [
            {name: getattr(event, name) for name in event.__dataclass_fields__}
            for event in events
        ]

    def invoke_tool(
        self, *, tool_name: str, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        handler = self.tool_handlers.get(tool_name)
        if handler is None:
            raise PermissionError("tool is not allowlisted")
        return handler(arguments)
