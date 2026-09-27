from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from cybercore.communication.agent_registry import AgentDescriptor, AgentRegistry
from cybercore.communication.contracts import RoomEvent, RoomEventDraft, TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.communication.test_agents import EchoAgent


class CyberHIVEEventGateway:
    """Translate the CyberCore EventGateway contract onto a CyberHIVE EventStore.

    CyberCore orchestration remains dependent on its EventGateway protocol. CyberHIVE
    implementation types are resolved only at this runtime composition boundary.
    """

    def __init__(self, event_store: Any, *, events_module: Any | None = None) -> None:
        self.event_store = event_store
        self._events_module = events_module

    def _events(self) -> Any:
        if self._events_module is None:
            self._events_module = import_module("cyberhive_core.communication_events")
        return self._events_module

    def _context(self, actor: TrustedActor) -> Any:
        return self._events().EventAccessContext(
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            room_ids=actor.room_ids,
            session_ids=actor.session_ids,
        )

    @staticmethod
    def _to_core(event: Any) -> RoomEvent:
        data = event.to_dict()
        return RoomEvent(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            sequence=data["sequence"],
            room_id=data["room_id"],
            session_id=data["session_id"],
            actor_id=data["actor_id"],
            actor_type=data["actor_type"],
            target=data["target"],
            event_type=data["event_type"],
            payload=data["payload"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata") or {},
            previous_hash=data.get("previous_hash"),
            event_hash=data.get("event_hash", ""),
        )

    def append(self, draft: RoomEventDraft, *, actor: TrustedActor) -> RoomEvent:
        event = self._events().CommunicationEvent.draft(
            event_id=draft.event_id,
            timestamp=draft.timestamp,
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
        )
        persisted = self.event_store.append(event, context=self._context(actor))
        return self._to_core(persisted)

    def read(
        self,
        room_id: str,
        session_id: str,
        *,
        actor: TrustedActor,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[RoomEvent, ...]:
        events = self.event_store.read(
            room_id,
            session_id,
            context=self._context(actor),
            after_sequence=after_sequence,
            limit=limit,
        )
        return tuple(self._to_core(event) for event in events)


@dataclass(slots=True)
class LocalMultiAgentRuntime:
    coordinator: RoomCoordinator
    event_store: Any
    runtime_bus: Any
    log_store: Any


def build_local_runtime(log_path: str | Path) -> LocalMultiAgentRuntime:
    """Compose Core orchestration with CyberHIVE's single-node communication ledger."""
    log_module = import_module("cyberhive_core.log_store")
    runtime_module = import_module("cyberhive_core.runtime_bus")
    state_module = import_module("cyberhive_core.state_engine")
    store_module = import_module("cyberhive_core.event_store")

    log_store = log_module.AppendOnlyLog(log_path)
    runtime_bus = runtime_module.RuntimeBus(
        node_id="cybercore.local",
        log_store=log_store,
        state_engine=state_module.StateEngine(),
    )
    event_store = store_module.RuntimeBusEventStore(
        runtime_bus=runtime_bus,
        log_store=log_store,
    )
    gateway = CyberHIVEEventGateway(event_store)

    agents = AgentRegistry()
    agents.register(
        AgentDescriptor(
            actor_id="agent-a",
            display_name="Agent A",
            handler=EchoAgent("A"),
            priority=10,
        )
    )
    agents.register(
        AgentDescriptor(
            actor_id="agent-b",
            display_name="Agent B",
            handler=EchoAgent("B"),
            priority=20,
        )
    )
    return LocalMultiAgentRuntime(
        coordinator=RoomCoordinator(gateway=gateway, agents=agents),
        event_store=event_store,
        runtime_bus=runtime_bus,
        log_store=log_store,
    )
