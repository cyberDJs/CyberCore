"""Open WebUI Pipe source for the CyberDJs Room integration.

This is source-controlled review material. Importing/enabling it in Open WebUI is a separate
runtime action and is intentionally outside this repository-only change.
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        CORE_URL: str = Field(default="http://127.0.0.1:8765")
        TIMEOUT_SECONDS: float = Field(default=30.0, ge=1.0, le=120.0)

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,
        __user__: dict | None = None,
        __chat_id__: str | None = None,
        __session_id__: str | None = None,
    ) -> str:
        messages = body.get("messages") or []
        user_messages = [item for item in messages if item.get("role") == "user"]
        if not user_messages:
            raise ValueError("CyberDJs Room requires a user message")
        text = str(user_messages[-1].get("content", "")).strip()
        if not text:
            raise ValueError("CyberDJs Room requires non-empty text")
        if not __chat_id__ or not __session_id__:
            raise ValueError("CyberDJs Room requires Open WebUI chat/session identity")

        user_id = str((__user__ or {}).get("id") or "").strip()
        if not user_id:
            raise ValueError("CyberDJs Room requires authenticated user identity")

        payload: dict[str, Any] = {
            "room_id": __chat_id__,
            "session_id": __session_id__,
            "text": text,
            "target": "*",
        }
        headers = {"X-CyberDJS-User-ID": user_id}
        url = self.valves.CORE_URL.rstrip("/") + "/v1/rooms/message"
        async with httpx.AsyncClient(timeout=self.valves.TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        replies = result.get("replies") or []
        if not isinstance(replies, list):
            raise RuntimeError("CyberCore returned malformed replies")

        rendered = []
        for reply in replies:
            name = str(reply.get("display_name") or reply.get("actor_id") or "agent")
            value = str(reply.get("text") or "")
            rendered.append(f"**{name}:** {value}")
        return "\n\n".join(rendered) or "No agent reply."
