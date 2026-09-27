from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from cybercore.communication.contracts import TrustedActor
from cybercore.communication.room_coordinator import RoomCoordinator

MAX_BODY_BYTES = 64 * 1024
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def handle_room_message(
    coordinator: RoomCoordinator,
    *,
    user_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Handle one trusted Open WebUI user turn without accepting actor_id from the body."""
    trusted_user_id = str(user_id or "").strip()
    room_id = str(payload.get("room_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    text = str(payload.get("text") or "").strip()
    target = str(payload.get("target") or "*").strip() or "*"

    if not trusted_user_id:
        raise PermissionError("trusted Open WebUI user identity is required")
    if not room_id or not session_id or not text:
        raise ValueError("room_id, session_id and text are required")

    actor = TrustedActor(
        actor_id=f"openwebui:{trusted_user_id}",
        actor_type="human",
        display_name=f"Open WebUI {trusted_user_id}",
        room_ids=(room_id,),
        session_ids=(session_id,),
    )
    events = coordinator.submit_text(
        room_id=room_id,
        session_id=session_id,
        actor=actor,
        text=text,
        target=target,
    )

    replies = [
        {
            "event_id": event.event_id,
            "sequence": event.sequence,
            "actor_id": event.actor_id,
            "display_name": str(event.metadata.get("display_name") or event.actor_id),
            "event_type": event.event_type,
            "text": str(event.payload.get("text") or ""),
        }
        for event in events[1:]
    ]
    return {
        "room_id": room_id,
        "session_id": session_id,
        "last_sequence": events[-1].sequence if events else 0,
        "replies": replies,
    }


def build_http_server(
    coordinator: RoomCoordinator,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    if host not in LOOPBACK_HOSTS:
        raise ValueError(
            "non-loopback room HTTP exposure requires separate deployment approval"
        )

    class RoomHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != "/v1/rooms/message":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    raise ValueError("invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("request body must be a JSON object")
                result = handle_room_message(
                    coordinator,
                    user_id=self.headers.get("X-CyberDJS-User-ID"),
                    payload=payload,
                )
                raw = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except PermissionError as exc:
                self.send_error(403, str(exc))
            except (ValueError, json.JSONDecodeError) as exc:
                self.send_error(400, str(exc))

        def log_message(self, format: str, *args: Any) -> None:
            return

    return ThreadingHTTPServer((host, port), RoomHandler)
