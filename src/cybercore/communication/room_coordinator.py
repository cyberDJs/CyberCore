from __future__ import annotations

import uuid

from .agent_registry import AgentRegistry
from .contracts import RoomEvent, RoomEventDraft, TrustedActor
from .event_gateway import EventGateway


class RoomCoordinator:
    """CyberCore-owned routing and floor control for one shared room history."""

    def __init__(self, *, gateway: EventGateway, agents: AgentRegistry) -> None:
        self.gateway = gateway
        self.agents = agents

    def submit_text(
        self,
        *,
        room_id: str,
        session_id: str,
        actor: TrustedActor,
        text: str,
        target: str = "*",
        event_id: str | None = None,
    ) -> tuple[RoomEvent, ...]:
        if not text.strip():
            raise ValueError("message text must not be empty")
        user_event = self.gateway.append(
            RoomEventDraft(
                event_id=event_id or f"evt_{uuid.uuid4().hex}",
                room_id=room_id,
                session_id=session_id,
                actor_id=actor.actor_id,
                actor_type=actor.actor_type,
                target=target,
                event_type="message.text",
                payload={"text": text},
            ),
            actor=actor,
        )
        appended: list[RoomEvent] = [user_event]
        for descriptor in self.agents.select(target):
            agent_actor = TrustedActor(
                actor_id=descriptor.actor_id,
                actor_type="agent",
                display_name=descriptor.display_name,
                room_ids=(room_id,),
                session_ids=(session_id,),
            )
            try:
                reply = descriptor.handler.respond(user_event)
                if reply is None:
                    continue
                appended.append(
                    self.gateway.append(
                        RoomEventDraft(
                            event_id=f"evt_{uuid.uuid4().hex}",
                            room_id=room_id,
                            session_id=session_id,
                            actor_id=descriptor.actor_id,
                            actor_type="agent",
                            target=actor.actor_id,
                            event_type="message.text",
                            payload={"text": reply.text},
                            correlation_id=user_event.event_id,
                            causation_id=user_event.event_id,
                            metadata={
                                "display_name": descriptor.display_name,
                                **dict(reply.metadata),
                            },
                        ),
                        actor=agent_actor,
                    )
                )
            except Exception as exc:
                system_actor = TrustedActor(
                    actor_id="cybercore.system",
                    actor_type="system",
                    display_name="CyberCore",
                    room_ids=(room_id,),
                    session_ids=(session_id,),
                )
                appended.append(
                    self.gateway.append(
                        RoomEventDraft(
                            event_id=f"evt_{uuid.uuid4().hex}",
                            room_id=room_id,
                            session_id=session_id,
                            actor_id=system_actor.actor_id,
                            actor_type=system_actor.actor_type,
                            target=actor.actor_id,
                            event_type="system.error",
                            payload={
                                "code": "agent_failed",
                                "agent_id": descriptor.actor_id,
                                "detail": type(exc).__name__,
                            },
                            correlation_id=user_event.event_id,
                            causation_id=user_event.event_id,
                        ),
                        actor=system_actor,
                    )
                )
        return tuple(appended)

    def submit_voice_transcript(
        self,
        *,
        room_id: str,
        session_id: str,
        actor: TrustedActor,
        transcript: str,
        target: str = "*",
        event_id: str | None = None,
    ) -> RoomEvent:
        if not transcript.strip():
            raise ValueError("transcript must not be empty")
        return self.gateway.append(
            RoomEventDraft(
                event_id=event_id or f"evt_{uuid.uuid4().hex}",
                room_id=room_id,
                session_id=session_id,
                actor_id=actor.actor_id,
                actor_type=actor.actor_type,
                target=target,
                event_type="message.voice.transcript",
                payload={"text": transcript},
            ),
            actor=actor,
        )

    def resume(
        self,
        *,
        room_id: str,
        session_id: str,
        actor: TrustedActor,
        after_sequence: int,
        limit: int = 100,
    ) -> tuple[RoomEvent, ...]:
        return self.gateway.read(
            room_id,
            session_id,
            actor=actor,
            after_sequence=after_sequence,
            limit=limit,
        )
