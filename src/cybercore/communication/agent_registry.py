from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import AgentReply, RoomEvent


class AgentHandler(Protocol):
    def respond(self, event: RoomEvent) -> AgentReply | None: ...


@dataclass(frozen=True, slots=True)
class AgentDescriptor:
    actor_id: str
    display_name: str
    handler: AgentHandler
    online: bool = True
    priority: int = 100
    voice_identity: str | None = None


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDescriptor] = {}

    def register(self, descriptor: AgentDescriptor) -> None:
        if not descriptor.actor_id.strip():
            raise ValueError("agent actor_id must not be empty")
        if descriptor.actor_id in self._agents:
            raise ValueError(f"agent already registered: {descriptor.actor_id}")
        self._agents[descriptor.actor_id] = descriptor

    def get(self, actor_id: str) -> AgentDescriptor | None:
        return self._agents.get(actor_id)

    def select(self, target: str) -> tuple[AgentDescriptor, ...]:
        if target == "*":
            agents = [item for item in self._agents.values() if item.online]
        else:
            one = self._agents.get(target)
            agents = [one] if one is not None and one.online else []
        return tuple(sorted(agents, key=lambda item: (item.priority, item.actor_id)))
