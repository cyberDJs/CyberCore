from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Mapping, Protocol

from cybercore.voice.models import IntentKind, Utterance, VoiceContext, VoiceIntent


MODEL_INTENT_KINDS = (
    IntentKind.QUESTION,
    IntentKind.SEARCH,
    IntentKind.INSPECT,
    IntentKind.PLAN,
    IntentKind.MONITOR,
    IntentKind.UNKNOWN,
)
DANGEROUS_INTENT_KINDS = frozenset({IntentKind.CANCEL, IntentKind.APPROVE, IntentKind.EXECUTE})

INTENT_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "kind": {"type": "string", "enum": [kind.value for kind in MODEL_INTENT_KINDS]},
        "operation": {"type": "string", "minLength": 1, "maxLength": 128},
        "target": {"type": ["string", "null"], "maxLength": 256},
        "language": {"type": "string", "minLength": 2, "maxLength": 16},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "needs_live_data": {"type": "boolean"},
    },
    "required": [
        "kind",
        "operation",
        "target",
        "language",
        "confidence",
        "needs_live_data",
    ],
}


class ModelClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, object] | None = None,
    ) -> str: ...


class CompileSource(StrEnum):
    SAFETY = "safety"
    MODEL = "model"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class ModelIntent:
    kind: IntentKind
    operation: str
    target: str | None
    language: str
    confidence: float
    needs_live_data: bool

    @classmethod
    def from_json(cls, value: str) -> ModelIntent:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"model intent is not valid JSON: {exc.msg}") from exc
        if not isinstance(decoded, Mapping):
            raise ValueError("model intent must be a JSON object")
        return cls.from_mapping(decoded)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ModelIntent:
        required = {
            "kind",
            "operation",
            "target",
            "language",
            "confidence",
            "needs_live_data",
        }
        if set(value) != required:
            extra = sorted(set(value) - required)
            missing = sorted(required - set(value))
            detail = []
            if missing:
                detail.append("missing=" + ",".join(missing))
            if extra:
                detail.append("extra=" + ",".join(extra))
            raise ValueError("model intent fields do not match schema: " + " ".join(detail))

        try:
            kind = IntentKind(str(value["kind"]))
        except ValueError as exc:
            raise ValueError("model intent kind is unknown") from exc
        if kind not in MODEL_INTENT_KINDS:
            raise ValueError("model cannot classify authority-sensitive intent kinds")

        operation = value["operation"]
        if not isinstance(operation, str) or not operation.strip() or len(operation) > 128:
            raise ValueError("model intent operation is invalid")

        target = value["target"]
        if target is not None and (not isinstance(target, str) or len(target) > 256):
            raise ValueError("model intent target is invalid")

        language = value["language"]
        if not isinstance(language, str) or not 2 <= len(language.strip()) <= 16:
            raise ValueError("model intent language is invalid")

        confidence = value["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("model intent confidence must be numeric")
        confidence_float = float(confidence)
        if not 0.0 <= confidence_float <= 1.0:
            raise ValueError("model intent confidence must be between 0 and 1")

        needs_live_data = value["needs_live_data"]
        if not isinstance(needs_live_data, bool):
            raise ValueError("model intent needs_live_data must be boolean")

        return cls(
            kind=kind,
            operation=operation.strip(),
            target=target.strip() if isinstance(target, str) and target.strip() else None,
            language=language.strip(),
            confidence=confidence_float,
            needs_live_data=needs_live_data,
        )

    def to_voice_intent(self, utterance: Utterance) -> VoiceIntent:
        return VoiceIntent(
            id=f"intent:{utterance.id}",
            utterance_id=utterance.id,
            kind=self.kind,
            operation=self.operation,
            target=self.target,
            confidence=self.confidence,
        )


@dataclass(frozen=True)
class CompiledIntent:
    intent: VoiceIntent
    source: CompileSource
    language: str = "und"
    needs_live_data: bool = False
    reason: str = ""


def model_context(context: VoiceContext) -> dict[str, object]:
    return {
        "project": context.project,
        "machine": context.machine,
        "active_plan_id": context.active_plan_id,
        "active_plan_revision": context.active_plan_revision,
        "target": context.references.get("target"),
    }
