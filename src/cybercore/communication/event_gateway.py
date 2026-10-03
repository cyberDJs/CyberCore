from __future__ import annotations

from typing import Protocol

from .contracts import RoomEvent, RoomEventDraft, TrustedActor


class EventGateway(Protocol):
    def append(self, draft: RoomEventDraft, *, actor: TrustedActor) -> RoomEvent: ...

    def read(
        self,
        room_id: str,
        session_id: str,
        *,
        actor: TrustedActor,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[RoomEvent, ...]: ...
