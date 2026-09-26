from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from cybercore.voice.intelligence.compiler import ModelIntentCompiler
from cybercore.voice.intelligence.composer import ModelResponseComposer
from cybercore.voice.intelligence.contracts import CompileSource
from cybercore.voice.models import (
    IntentKind,
    ResponseStatus,
    Utterance,
    VoiceContext,
    VoiceIntent,
    VoiceResponse,
)
from cybercore.voice.router import VoiceRouter
from cybercore.voice.session import VoiceSession


@dataclass(frozen=True)
class ControllerResponse:
    status: str
    message: str
    intent: VoiceIntent
    routed_response: VoiceResponse | None = None

    @property
    def cancelled(self) -> bool:
        return bool(
            self.routed_response is not None
            and self.routed_response.status is ResponseStatus.CANCELLED
        )


class _FixedIntentCompiler:
    def __init__(self, intent: VoiceIntent) -> None:
        self.intent = intent

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent:
        return self.intent


_LIVE_DATA_INTENT_KINDS = frozenset({IntentKind.SEARCH, IntentKind.INSPECT, IntentKind.MONITOR})
_LEXICAL_DEFINITION_PATTERNS = (
    re.compile(r"what does (?P<term>[a-z0-9_-]{1,64}) mean"),
    re.compile(r"define (?P<term>[a-z0-9_-]{1,64})"),
    re.compile(r"co znamena (?P<term>[a-z0-9_-]{1,64})"),
    re.compile(r"definuj (?P<term>[a-z0-9_-]{1,64})"),
)


def _normalize_query(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^\w\s-]", " ", asciiish)
    return " ".join(words_only.strip().split())


def _is_explicit_lexical_definition(text: str) -> bool:
    normalized = _normalize_query(text)
    return any(pattern.fullmatch(normalized) for pattern in _LEXICAL_DEFINITION_PATTERNS)


def _requires_live_data(utterance: Utterance, intent: VoiceIntent) -> bool:
    if intent.kind in _LIVE_DATA_INTENT_KINDS:
        return True
    if intent.kind is IntentKind.QUESTION:
        return not _is_explicit_lexical_definition(utterance.text)
    return False


class IntelligentVoiceController:
    def __init__(
        self,
        *,
        compiler: ModelIntentCompiler,
        composer: ModelResponseComposer,
        router: VoiceRouter | None = None,
    ) -> None:
        self.compiler = compiler
        self.composer = composer
        self.router = router or VoiceRouter()

    def handle(
        self,
        utterance: Utterance,
        context: VoiceContext,
        *,
        session: VoiceSession | None = None,
    ) -> ControllerResponse:
        compiled = self.compiler.compile_result(utterance, context)
        intent = compiled.intent
        requires_live_data = compiled.needs_live_data or _requires_live_data(utterance, intent)

        if (
            compiled.source is CompileSource.MODEL
            and intent.kind is IntentKind.QUESTION
            and not requires_live_data
        ):
            if session is not None:
                session.mark_intent(intent.id)
            try:
                message = self.composer.answer(
                    utterance,
                    context,
                    language=compiled.language,
                )
            except (OSError, RuntimeError, TimeoutError, ValueError):
                message = "Model response is unavailable; no action was taken."
                status = "model_unavailable"
            else:
                status = "answered"
            return ControllerResponse(status=status, message=message, intent=intent)

        if compiled.source is CompileSource.MODEL and requires_live_data:
            if session is not None:
                session.mark_intent(intent.id)
            message = (
                "Potřebuji živá data z povoleného read-only nástroje; nic si nebudu domýšlet."
                if compiled.language.lower().startswith("cs")
                else "I need live data from an allowed read-only tool; I will not invent it."
            )
            return ControllerResponse(status="needs_live_data", message=message, intent=intent)

        routed = VoiceRouter(
            compiler=_FixedIntentCompiler(intent),
            planner=self.router.planner,
            howedo=self.router.howedo,
            oathdo=self.router.oathdo,
            approval_verifier=self.router.approval_verifier,
            event_sink=self.router.event_sink,
        ).handle(utterance, context, session=session)
        return ControllerResponse(
            status=routed.status.value,
            message=routed.message,
            intent=intent,
            routed_response=routed,
        )


def build_intelligent_voice_controller(config, *, router: VoiceRouter | None = None):
    from cybercore.voice.intelligence.ollama import OllamaModelClient

    client = OllamaModelClient(config)
    compiler = ModelIntentCompiler(client, min_confidence=config.min_confidence)
    composer = ModelResponseComposer(client, max_answer_chars=config.max_answer_chars)
    return IntelligentVoiceController(compiler=compiler, composer=composer, router=router)
