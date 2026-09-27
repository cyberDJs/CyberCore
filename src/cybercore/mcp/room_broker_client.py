from __future__ import annotations

import json
from pathlib import Path
import socket
from typing import Any, Mapping

from cybercore.communication.contracts import TrustedActor

_MAX_RESPONSE_BYTES = 1024 * 1024


class BrokerRoomBackend:
    """Room backend proxy bound to the identity of one broker Unix socket."""

    def __init__(self, socket_path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.socket_path = Path(socket_path)
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("timeout_seconds must be between 0 and 30")
        self.timeout_seconds = float(timeout_seconds)
        identity = self._call("identity", {})
        if not isinstance(identity, dict):
            raise RuntimeError("broker returned malformed identity")
        self.actor = TrustedActor(
            actor_id=str(identity["actor_id"]),
            actor_type=str(identity["actor_type"]),
            display_name=str(identity["display_name"]),
            room_ids=tuple(str(item) for item in identity.get("authorized_rooms") or ()),
        )

    def _call(
        self,
        method: str,
        args: Mapping[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> object:
        request = (
            json.dumps(
                {"method": method, "args": dict(args)},
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        transport_timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(transport_timeout)
            client.connect(str(self.socket_path))
            client.sendall(request)
            with client.makefile("rb") as stream:
                line = stream.readline(_MAX_RESPONSE_BYTES + 1)
        if not line or len(line) > _MAX_RESPONSE_BYTES:
            raise RuntimeError("broker returned no valid response")
        response = json.loads(line)
        if not isinstance(response, dict) or response.get("ok") is not True:
            error = response.get("error") if isinstance(response, dict) else None
            error_type = error.get("type") if isinstance(error, dict) else "BrokerError"
            raise RuntimeError(f"broker call failed: {error_type}")
        return response.get("result")

    def post_event(
        self,
        *,
        room_id: str,
        session_id: str,
        target: str,
        event_type: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        result = self._call(
            "post_event",
            {
                "room_id": room_id,
                "session_id": session_id,
                "target": target,
                "event_type": event_type,
                "payload": dict(payload),
            },
        )
        if not isinstance(result, dict):
            raise RuntimeError("broker returned malformed event")
        return result

    def read_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        result = self._call(
            "read_events",
            {
                "room_id": room_id,
                "session_id": session_id,
                "after_sequence": after_sequence,
                "limit": limit,
            },
        )
        if not isinstance(result, list):
            raise RuntimeError("broker returned malformed event list")
        return [dict(item) for item in result if isinstance(item, dict)]

    def subscribe_events(
        self,
        *,
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
        wait_seconds: float = 1.0,
    ) -> list[dict[str, Any]]:
        bounded_wait = max(0.0, min(float(wait_seconds), 5.0))
        result = self._call(
            "subscribe_events",
            {
                "room_id": room_id,
                "session_id": session_id,
                "after_sequence": after_sequence,
                "limit": limit,
                "wait_seconds": bounded_wait,
            },
            timeout_seconds=max(self.timeout_seconds, bounded_wait + 1.0),
        )
        if not isinstance(result, list):
            raise RuntimeError("broker returned malformed subscription result")
        return [dict(item) for item in result if isinstance(item, dict)]

    def get_runtime_status(self) -> Mapping[str, Any]:
        result = self._call("runtime_status", {})
        if not isinstance(result, dict):
            raise RuntimeError("broker returned malformed runtime status")
        return result
