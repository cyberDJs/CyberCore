from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any, Iterable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_ROOM_ID = "cyberdjs-main"
DEFAULT_SESSION_PREFIX = "slack"
DEFAULT_SOCKET_NAMES = {
    "chatgpt:johnny-work": "johnny-work.sock",
    "chatgpt:johnny-mod": "johnny-mod.sock",
    "chatgpt:eimy": "eimy.sock",
}


@dataclass(frozen=True, slots=True)
class SlackIngressMessage:
    channel_id: str
    message_ts: str
    user_id: str
    text: str

    @classmethod
    def from_slack(cls, channel_id: str, raw: Mapping[str, Any]) -> "SlackIngressMessage | None":
        subtype = str(raw.get("subtype") or "")
        if subtype in {"channel_join", "channel_leave", "message_changed", "message_deleted", "bot_message"}:
            return None
        user_id = str(raw.get("user") or "").strip()
        message_ts = str(raw.get("ts") or "").strip()
        text = str(raw.get("text") or "")
        if not user_id or not message_ts or not text.strip():
            return None
        return cls(channel_id=channel_id, message_ts=message_ts, user_id=user_id, text=text)


class BrokerSocketClient:
    def __init__(self, socket_path: str | Path, *, timeout_seconds: float = 3.0) -> None:
        self.socket_path = str(socket_path)
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, **args: Any) -> Any:
        request = json.dumps({"method": method, "args": args}, separators=(",", ":")).encode() + b"\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(self.timeout_seconds)
            client.connect(self.socket_path)
            client.sendall(request)
            response = b""
            while not response.endswith(b"\n"):
                chunk = client.recv(65536)
                if not chunk:
                    break
                response += chunk
        if not response:
            raise RuntimeError("room broker returned no response")
        decoded = json.loads(response)
        if not decoded.get("ok"):
            error = decoded.get("error") or {}
            raise RuntimeError(f"room broker request failed: {error.get('type', 'unknown')}")
        return decoded.get("result")

    def post(self, *, room_id: str, session_id: str, target: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        result = self._request(
            "post_event",
            room_id=room_id,
            session_id=session_id,
            target=target,
            event_type="message.text",
            payload=dict(payload),
        )
        if not isinstance(result, dict):
            raise RuntimeError("room broker returned invalid post result")
        return result

    def read(self, *, room_id: str, session_id: str, after_sequence: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        result = self._request(
            "read_events",
            room_id=room_id,
            session_id=session_id,
            after_sequence=after_sequence,
            limit=limit,
        )
        if not isinstance(result, list):
            raise RuntimeError("room broker returned invalid read result")
        return [item for item in result if isinstance(item, dict)]


class SlackWebApi:
    def __init__(self, token: str, *, timeout_seconds: float = 5.0) -> None:
        token = token.strip()
        if not token:
            raise ValueError("Slack token is required")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def history(self, *, channel_id: str, oldest: str | None = None) -> list[Mapping[str, Any]]:
        cursor: str | None = None
        messages: list[Mapping[str, Any]] = []
        while True:
            params = {"channel": channel_id, "limit": "200", "inclusive": "false"}
            if oldest:
                params["oldest"] = oldest
            if cursor:
                params["cursor"] = cursor
            request = Request(
                "https://slack.com/api/conversations.history?" + urlencode(params),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read())
            if not payload.get("ok"):
                raise RuntimeError(f"Slack conversations.history failed: {payload.get('error', 'unknown')}")
            batch = payload.get("messages") or []
            messages.extend(item for item in batch if isinstance(item, dict))
            metadata = payload.get("response_metadata") or {}
            cursor = str(metadata.get("next_cursor") or "").strip() or None
            if not cursor:
                break
        return messages


class SlackRoomIngress:
    def __init__(
        self,
        *,
        room_id: str,
        channel_id: str,
        user_map: Mapping[str, str],
        socket_dir: str | Path,
        session_prefix: str = DEFAULT_SESSION_PREFIX,
    ) -> None:
        self.room_id = room_id
        self.channel_id = channel_id
        self.user_map = dict(user_map)
        self.socket_dir = Path(socket_dir)
        self.session_id = f"{session_prefix}-{channel_id}"

    def _client_for(self, actor_id: str) -> BrokerSocketClient:
        socket_name = DEFAULT_SOCKET_NAMES.get(actor_id)
        if socket_name is None:
            raise PermissionError(f"Slack user maps to unsupported room identity: {actor_id}")
        return BrokerSocketClient(self.socket_dir / socket_name)

    def _already_ingested(self, client: BrokerSocketClient, message: SlackIngressMessage) -> bool:
        for event in client.read(room_id=self.room_id, session_id=self.session_id):
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if (
                payload.get("transport") == "slack"
                and payload.get("slack_channel_id") == message.channel_id
                and payload.get("slack_message_ts") == message.message_ts
            ):
                return True
        return False

    def ingest(self, message: SlackIngressMessage) -> dict[str, Any] | None:
        actor_id = self.user_map.get(message.user_id)
        if actor_id is None:
            return None
        client = self._client_for(actor_id)
        if self._already_ingested(client, message):
            return None
        return client.post(
            room_id=self.room_id,
            session_id=self.session_id,
            target="*",
            payload={
                "text": message.text,
                "transport": "slack",
                "slack_channel_id": message.channel_id,
                "slack_message_ts": message.message_ts,
                "slack_user_id": message.user_id,
            },
        )

    def ingest_many(self, raw_messages: Iterable[Mapping[str, Any]]) -> tuple[int, str | None]:
        accepted = 0
        max_ts: str | None = None
        normalized: list[SlackIngressMessage] = []
        for raw in raw_messages:
            raw_ts = str(raw.get("ts") or "").strip()
            if raw_ts:
                if max_ts is None or float(raw_ts) > float(max_ts):
                    max_ts = raw_ts
            message = SlackIngressMessage.from_slack(self.channel_id, raw)
            if message is not None:
                normalized.append(message)
        normalized.sort(key=lambda item: float(item.message_ts))
        for message in normalized:
            if self.ingest(message) is not None:
                accepted += 1
        return accepted, max_ts


def _load_user_map(raw: str) -> dict[str, str]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("CYBERDJS_SLACK_USER_MAP must be a JSON object")
    result = {str(key): str(value) for key, value in parsed.items()}
    for user_id, actor_id in result.items():
        if not user_id.startswith("U"):
            raise ValueError("Slack user IDs must start with U")
        if actor_id not in DEFAULT_SOCKET_NAMES:
            raise ValueError(f"unsupported room identity in user map: {actor_id}")
    return result


def _read_state(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    value = str(payload.get("last_ts") or "").strip()
    return value or None


def _write_state(path: Path, last_ts: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"last_ts": last_ts}, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge one Slack channel into the CyberDJS Room broker")
    parser.add_argument("--once", action="store_true", help="poll Slack once and exit")
    parser.add_argument("--stdin-json", action="store_true", help="read one Slack API message JSON object per line")
    parser.add_argument("--interval", type=float, default=2.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    channel_id = os.environ["CYBERDJS_SLACK_ROOM_CHANNEL_ID"].strip()
    room_id = os.environ.get("CYBERDJS_ROOM_ID", DEFAULT_ROOM_ID).strip()
    socket_dir = os.environ.get("CYBERDJS_ROOM_SOCKET_DIR", "/run/cyberdjs-room").strip()
    user_map = _load_user_map(os.environ["CYBERDJS_SLACK_USER_MAP"])
    ingress = SlackRoomIngress(
        room_id=room_id,
        channel_id=channel_id,
        user_map=user_map,
        socket_dir=socket_dir,
    )

    if args.stdin_json:
        raw = [json.loads(line) for line in sys.stdin if line.strip()]
        count, _ = ingress.ingest_many(raw)
        print(json.dumps({"ok": True, "ingested": count}, separators=(",", ":")))
        return 0

    token = os.environ.get("CYBERDJS_SLACK_BOT_TOKEN", "")
    api = SlackWebApi(token)
    state_path = Path(
        os.environ.get(
            "CYBERDJS_SLACK_INGRESS_STATE",
            "/var/lib/cyberhive-persist/cyberdjs-room/slack-ingress-state.json",
        )
    )

    while True:
        oldest = _read_state(state_path)
        messages = api.history(channel_id=channel_id, oldest=oldest)
        _, max_ts = ingress.ingest_many(messages)
        if max_ts is not None:
            _write_state(state_path, max_ts)
        if args.once:
            return 0
        time.sleep(max(0.5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
