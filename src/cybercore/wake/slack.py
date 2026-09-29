from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .dispatcher import WakeRequest


class SlackIncomingWebhookWakeSink:
    """Minimal Slack wake adapter.

    The webhook URL is supplied at runtime from a secret source. Room message content is
    intentionally not sent to Slack; the woken ChatGPT instance reads the canonical event
    from CyberHIVE through the MCP room app.
    """

    def __init__(self, webhook_url: str, *, timeout_seconds: float = 3.0) -> None:
        webhook_url = webhook_url.strip()
        if not webhook_url:
            raise ValueError("Slack webhook URL is required")
        parsed = urlparse(webhook_url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "hooks.slack.com",
            "hooks.slack-gov.com",
        }:
            raise ValueError("Slack webhook URL must use an approved Slack HTTPS host")
        if timeout_seconds <= 0 or timeout_seconds > 15:
            raise ValueError("timeout_seconds must be between 0 and 15")
        self._webhook_url = webhook_url
        self.timeout_seconds = float(timeout_seconds)

    @staticmethod
    def render(request: WakeRequest) -> str:
        return "\n".join(
            (
                "CYBERDJS_WAKE",
                f"target={request.target}",
                f"room={request.room_id}",
                f"session={request.session_id}",
                f"event={request.event_id}",
                f"sequence={request.sequence}",
                f"type={request.event_type}",
            )
        )

    def send(self, request: WakeRequest) -> None:
        payload = json.dumps({"text": self.render(request)}).encode("utf-8")
        http_request = Request(
            self._webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(http_request, timeout=self.timeout_seconds) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Slack webhook returned HTTP {response.status}")
