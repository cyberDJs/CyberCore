from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cybercore.communication.contracts import TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator
from cybercore.cyberhive_runtime import LocalMultiAgentRuntime, build_local_runtime
from cybercore.mcp.backend import RoomCommunicationBackend
from cybercore.wake.dispatcher import WakeDispatcher
from cybercore.wake.gateway import WakeAwareEventGateway
from cybercore.wake.slack import SlackIncomingWebhookWakeSink

ALLOWED_CHATGPT_IDENTITIES = frozenset({"chatgpt:johnny", "chatgpt:eimy"})
DEFAULT_DISPLAY_NAMES = {
    "chatgpt:johnny": "Johnny AI",
    "chatgpt:eimy": "Eimy AI",
}


@dataclass(slots=True)
class CyberDJSRoomRuntime:
    backend: RoomCommunicationBackend
    dispatcher: WakeDispatcher
    local_runtime: LocalMultiAgentRuntime

    def close(self) -> None:
        self.dispatcher.drain(timeout_seconds=2.0)
        self.dispatcher.stop(timeout_seconds=2.0)


def build_cyberdjs_room_runtime(
    log_path: str | Path,
    *,
    actor_id: str,
    room_id: str = "cyberdjs-main",
    display_name: str | None = None,
    slack_webhook_url: str | None = None,
) -> CyberDJSRoomRuntime:
    actor_id = actor_id.strip()
    room_id = room_id.strip()
    if actor_id not in ALLOWED_CHATGPT_IDENTITIES:
        raise ValueError("actor_id must be one of the governed ChatGPT room identities")
    if not room_id:
        raise ValueError("room_id must not be empty")

    base = build_local_runtime(log_path)
    sinks: dict[str, Any] = {}
    if slack_webhook_url:
        sink = SlackIncomingWebhookWakeSink(slack_webhook_url)
        sinks = {identity: sink for identity in ALLOWED_CHATGPT_IDENTITIES}

    dispatcher = WakeDispatcher(sinks)
    dispatcher.start()
    gateway = WakeAwareEventGateway(base.coordinator.gateway, dispatcher)
    coordinator = RoomCoordinator(gateway=gateway, agents=base.coordinator.agents)
    actor = TrustedActor(
        actor_id=actor_id,
        actor_type="agent",
        display_name=(display_name or DEFAULT_DISPLAY_NAMES[actor_id]).strip(),
        room_ids=(room_id,),
    )

    def runtime_status() -> dict[str, object]:
        return {
            "state": "ready",
            "actor_id": actor.actor_id,
            "room_id": room_id,
            "last_sequence": base.event_store.last_sequence,
            "ledger_integrity": base.event_store.verify_integrity(),
            "wake_enabled": bool(sinks),
        }

    backend = RoomCommunicationBackend(
        coordinator=coordinator,
        actor=actor,
        runtime_status=runtime_status,
    )
    return CyberDJSRoomRuntime(
        backend=backend,
        dispatcher=dispatcher,
        local_runtime=base,
    )
