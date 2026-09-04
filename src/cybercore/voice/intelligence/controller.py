from __future__ import annotations

from dataclasses import dataclass

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

        if (
            compiled.source is CompileSource.MODEL
            and intent.kind is IntentKind.QUESTION
            and not compiled.needs_live_data
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

        if compiled.source is CompileSource.MODEL and compiled.needs_live_data:
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
