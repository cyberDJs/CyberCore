from __future__ import annotations

import json

from cybercore.voice.intelligence.contracts import ModelClient, model_context
from cybercore.voice.models import Utterance, VoiceContext


_LIVE_SENTINEL = "LIVE_DATA_REQUIRED"
_SYSTEM_PROMPT = f"""You are the general-knowledge response composer for Cyber Voice.
Answer briefly and naturally in the user's language. You have no tools and no current external
state. Never claim to know current repository, service, CI, machine, infrastructure, account,
market, weather, news, or other changing state. If live/current data is required, output exactly
{_LIVE_SENTINEL}. Never claim that an action was executed, approved, scheduled, or verified."""


class ModelResponseComposer:
    def __init__(self, client: ModelClient, *, max_answer_chars: int = 1200) -> None:
        self.client = client
        self.max_answer_chars = max_answer_chars

    def answer(
        self,
        utterance: Utterance,
        context: VoiceContext,
        *,
        language: str = "und",
    ) -> str:
        payload = {
            "utterance": utterance.text,
            "language": language,
            "context": model_context(context),
        }
        response = self.client.complete(
            system=_SYSTEM_PROMPT,
            user=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        )
        if response.strip() == _LIVE_SENTINEL:
            raise RuntimeError("model refused general answer because live data is required")
        if len(response) > self.max_answer_chars:
            response = response[: self.max_answer_chars].rstrip() + "…"
        return response
