from __future__ import annotations

from cybercore.communication.contracts import RoomEvent, RoomEventDraft, TrustedActor
from cybercore.communication.event_gateway import EventGateway

from .dispatcher import WakeDispatcher


class WakeAwareEventGateway:
    """Decorate an EventGateway with best-effort wake dispatch after persistence."""

    def __init__(self, delegate: EventGateway, dispatcher: WakeDispatcher) -> None:
        self.delegate = delegate
        self.dispatcher = dispatcher

    def append(self, draft: RoomEventDraft, *, actor: TrustedActor) -> RoomEvent:
        persisted = self.delegate.append(draft, actor=actor)
        self.dispatcher.submit(persisted)
        return persisted

    def read(
        self,
        room_id: str,
        session_id: str,
        *,
        actor: TrustedActor,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[RoomEvent, ...]:
        return self.delegate.read(
            room_id,
            session_id,
            actor=actor,
            after_sequence=after_sequence,
            limit=limit,
        )
