from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class TrustedActor:
    actor_id: str
    actor_type: str
    display_name: str
    room_ids: tuple[str, ...]
    session_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoomEventDraft:
    event_id: str
    room_id: str
    session_id: str
    actor_id: str
    actor_type: str
    target: str
    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True, slots=True)
class RoomEvent:
    event_id: str
    timestamp: str
    sequence: int
    room_id: str
    session_id: str
    actor_id: str
    actor_type: str
    target: str
    event_type: str
    payload: Mapping[str, Any]
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    previous_hash: str | None = None
    event_hash: str = ""


@dataclass(frozen=True, slots=True)
class AgentReply:
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
