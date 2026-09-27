from __future__ import annotations

from dataclasses import dataclass

from .contracts import AgentReply, RoomEvent


@dataclass
class EchoAgent:
    prefix: str

    def respond(self, event: RoomEvent) -> AgentReply:
        return AgentReply(text=f"{self.prefix}: {event.payload.get('text', '')}")


class FailingAgent:
    def respond(self, event: RoomEvent) -> AgentReply:
        raise RuntimeError("deterministic test failure")
