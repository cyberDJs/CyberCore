#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import urllib.request

from cybercore.communication.contracts import TrustedActor
from cybercore.communication.http_runtime import build_http_server, handle_room_message
from cybercore.cyberhive_runtime import build_local_runtime


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "runtime.jsonl"
        runtime = build_local_runtime(log_path)

        server = build_http_server(runtime.coordinator, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]

        body = json.dumps(
            {
                "room_id": "room-1",
                "session_id": "session-1",
                "text": "hello team",
                "target": "*",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/rooms/message",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-CyberDJS-User-ID": "user-1",
            },
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(request, timeout=5).read())

        server.shutdown()
        thread.join(timeout=2)

        assert [reply["actor_id"] for reply in response["replies"]] == [
            "agent-a",
            "agent-b",
        ]

        actor = TrustedActor(
            actor_id="openwebui:user-1",
            actor_type="human",
            display_name="User 1",
            room_ids=("room-1",),
            session_ids=("session-1",),
        )
        initial = runtime.coordinator.resume(
            room_id="room-1",
            session_id="session-1",
            actor=actor,
            after_sequence=0,
        )
        assert [event.sequence for event in initial] == [1, 2, 3]
        assert [event.actor_id for event in initial] == [
            "openwebui:user-1",
            "agent-a",
            "agent-b",
        ]
        assert runtime.event_store.verify_integrity()

        restarted = build_local_runtime(log_path)
        resumed = restarted.coordinator.resume(
            room_id="room-1",
            session_id="session-1",
            actor=actor,
            after_sequence=1,
        )
        assert [event.sequence for event in resumed] == [2, 3]

        second = handle_room_message(
            restarted.coordinator,
            user_id="user-1",
            payload={
                "room_id": "room-1",
                "session_id": "session-1",
                "text": "after restart",
                "target": "*",
            },
        )
        assert second["last_sequence"] == 6

        voice = restarted.coordinator.submit_voice_transcript(
            room_id="room-1",
            session_id="session-1",
            actor=actor,
            transcript="voice transcript",
        )
        assert voice.sequence == 7
        assert voice.event_type == "message.voice.transcript"
        assert restarted.event_store.verify_integrity()

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "http_replies": [
                        reply["actor_id"] for reply in response["replies"]
                    ],
                    "initial_sequences": [event.sequence for event in initial],
                    "resume_after_1": [event.sequence for event in resumed],
                    "post_restart_last_sequence": second["last_sequence"],
                    "voice_sequence": voice.sequence,
                    "log_frames": restarted.log_store.count(),
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
