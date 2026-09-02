from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Mapping


class VoiceEventType(StrEnum):
    UTTERANCE_RECEIVED = "utterance_received"
    INTENT_CLASSIFIED = "intent_classified"
    CONTINUITY_EVALUATED = "continuity_evaluated"
    GOVERNANCE_EVALUATED = "governance_evaluated"
    APPROVAL_INTENT_CAPTURED = "approval_intent_captured"
    ACTION_BLOCKED = "action_blocked"
    ACTION_READY = "action_ready"
    CANCELLED = "cancelled"
    RESPONSE_EMITTED = "response_emitted"


@dataclass(frozen=True)
class VoiceEvent:
    type: VoiceEventType
    session_id: str
    utterance_id: str
    detail: Mapping[str, str] = field(default_factory=dict)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
