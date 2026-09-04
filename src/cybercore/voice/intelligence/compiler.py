from __future__ import annotations

import json

from cybercore.voice.intelligence.contracts import (
    CompiledIntent,
    CompileSource,
    DANGEROUS_INTENT_KINDS,
    INTENT_SCHEMA,
    ModelClient,
    ModelIntent,
    model_context,
)
from cybercore.voice.intelligence.safety import SafetyIntentGuard
from cybercore.voice.models import IntentKind, Utterance, VoiceContext, VoiceIntent
from cybercore.voice.router import RuleIntentCompiler


_SYSTEM_PROMPT = """You classify spoken Cyber Voice utterances into a strict JSON schema.
You are not an authorization system and never grant permission or execution authority.
Authority-sensitive CANCEL, APPROVE, and EXECUTE commands are handled outside the model and
are intentionally absent from your schema. Classify requests for current project, machine,
repository, service, CI, infrastructure, or changing external state with needs_live_data=true.
Use needs_live_data=false only for stable general-knowledge questions that can be answered
without tools or current sources. Do not invent targets or current state."""


class ModelIntentCompiler:
    def __init__(
        self,
        client: ModelClient,
        *,
        min_confidence: float = 0.75,
        safety_guard: SafetyIntentGuard | None = None,
        fallback: RuleIntentCompiler | None = None,
    ) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        self.client = client
        self.min_confidence = min_confidence
        self.safety_guard = safety_guard or SafetyIntentGuard()
        self.fallback = fallback or RuleIntentCompiler()

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent:
        return self.compile_result(utterance, context).intent

    def compile_result(self, utterance: Utterance, context: VoiceContext) -> CompiledIntent:
        safety_intent = self.safety_guard.compile(utterance, context)
        if safety_intent is not None:
            return CompiledIntent(
                intent=safety_intent,
                source=CompileSource.SAFETY,
                reason="authority-sensitive intent classified deterministically",
            )

        user_payload = {
            "utterance": utterance.text,
            "context": model_context(context),
            "schema": INTENT_SCHEMA,
        }
        try:
            response = self.client.complete(
                system=_SYSTEM_PROMPT,
                user=json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
                schema=INTENT_SCHEMA,
            )
            model_intent = ModelIntent.from_json(response)
        except (OSError, RuntimeError, TimeoutError, ValueError):
            return self._fallback(utterance, context, "model unavailable or invalid")

        if model_intent.confidence < self.min_confidence:
            return self._fallback(utterance, context, "model confidence below threshold")
        return CompiledIntent(
            intent=model_intent.to_voice_intent(utterance),
            source=CompileSource.MODEL,
            language=model_intent.language,
            needs_live_data=model_intent.needs_live_data,
            reason="validated structured model classification",
        )

    def _fallback(
        self,
        utterance: Utterance,
        context: VoiceContext,
        reason: str,
    ) -> CompiledIntent:
        intent = self.fallback.compile(utterance, context)
        if intent.kind in DANGEROUS_INTENT_KINDS:
            intent = VoiceIntent(
                id=f"intent:{utterance.id}",
                utterance_id=utterance.id,
                kind=IntentKind.UNKNOWN,
                operation=IntentKind.UNKNOWN.value,
                target=context.references.get("target"),
                confidence=0.0,
            )
        return CompiledIntent(
            intent=intent,
            source=CompileSource.FALLBACK,
            reason=reason,
        )
