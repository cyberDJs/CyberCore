from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from cybercore.integrations.howedo import (
    ContinuityDecision,
    FailClosedHowedoGateway,
    HowedoGateway,
)
from cybercore.integrations.oathdo import (
    FailClosedOathdoGateway,
    GovernanceDecision,
    OathdoGateway,
)
from cybercore.voice.approval import (
    ApprovalVerifier,
    DenyAllApprovalVerifier,
    capture_voice_approval_intent,
)
from cybercore.voice.events import VoiceEvent, VoiceEventType
from cybercore.voice.models import (
    ActionRequest,
    IntentKind,
    ResponseStatus,
    Utterance,
    VoiceContext,
    VoiceIntent,
    VoiceResponse,
)
from cybercore.voice.session import VoiceSession


class IntentCompiler(Protocol):
    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent: ...


class ActionPlanner(Protocol):
    def plan(self, intent: VoiceIntent, context: VoiceContext) -> ActionRequest | None: ...


class RuleIntentCompiler:
    _CANCEL = ("cancel", "stop", "abort", "zrus", "storno")
    _APPROVE = ("approve", "schvalu", "souhlas", "jo udelej", "ano proved")
    _EXECUTE = ("execute", "apply", "run", "proved", "spust", "udelej")
    _PLAN = ("plan", "naplanuj", "priprav")
    _MONITOR = ("monitor", "watch", "hlidej", "sleduj")
    _INSPECT = ("inspect", "check", "prover", "zkontroluj")
    _SEARCH = ("search", "find", "najdi", "hledej")

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent:
        text = utterance.text.strip().lower()
        kind = IntentKind.UNKNOWN
        for candidate, markers in (
            (IntentKind.CANCEL, self._CANCEL),
            (IntentKind.APPROVE, self._APPROVE),
            (IntentKind.EXECUTE, self._EXECUTE),
            (IntentKind.PLAN, self._PLAN),
            (IntentKind.MONITOR, self._MONITOR),
            (IntentKind.INSPECT, self._INSPECT),
            (IntentKind.SEARCH, self._SEARCH),
        ):
            if any(marker in text for marker in markers):
                kind = candidate
                break
        if kind is IntentKind.UNKNOWN and text.endswith("?"):
            kind = IntentKind.QUESTION
        return VoiceIntent(
            id=f"intent:{utterance.id}",
            utterance_id=utterance.id,
            kind=kind,
            operation=kind.value,
            target=context.references.get("target"),
            confidence=1.0 if kind is not IntentKind.UNKNOWN else 0.0,
        )


class NoopActionPlanner:
    def plan(self, intent: VoiceIntent, context: VoiceContext) -> ActionRequest | None:
        return None


EventSink = Callable[[VoiceEvent], None]


class VoiceRouter:
    def __init__(
        self,
        *,
        compiler: IntentCompiler | None = None,
        planner: ActionPlanner | None = None,
        howedo: HowedoGateway | None = None,
        oathdo: OathdoGateway | None = None,
        approval_verifier: ApprovalVerifier | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.compiler = compiler or RuleIntentCompiler()
        self.planner = planner or NoopActionPlanner()
        self.howedo = howedo or FailClosedHowedoGateway()
        self.oathdo = oathdo or FailClosedOathdoGateway()
        self.approval_verifier = approval_verifier or DenyAllApprovalVerifier()
        self.event_sink = event_sink

    def _emit(
        self,
        event_type: VoiceEventType,
        utterance: Utterance,
        **detail: str,
    ) -> None:
        if self.event_sink is None:
            return
        self.event_sink(
            VoiceEvent(
                type=event_type,
                session_id=utterance.session_id,
                utterance_id=utterance.id,
                detail=detail,
            )
        )

    def _response(
        self,
        utterance: Utterance,
        intent: VoiceIntent,
        *,
        status: ResponseStatus,
        message: str,
        action: ActionRequest | None = None,
        continuity_decision: str | None = None,
        governance_decision: str | None = None,
        approval_id: str | None = None,
        approval_intent_id: str | None = None,
    ) -> VoiceResponse:
        response = VoiceResponse(
            status=status,
            message=message,
            intent=intent,
            action=action,
            continuity_decision=continuity_decision,
            governance_decision=governance_decision,
            approval_id=approval_id,
            approval_intent_id=approval_intent_id,
        )
        self._emit(VoiceEventType.RESPONSE_EMITTED, utterance, status=status.value)
        return response

    def handle(
        self,
        utterance: Utterance,
        context: VoiceContext,
        *,
        session: VoiceSession | None = None,
    ) -> VoiceResponse:
        self._emit(VoiceEventType.UTTERANCE_RECEIVED, utterance)
        intent = self.compiler.compile(utterance, context)
        self._emit(VoiceEventType.INTENT_CLASSIFIED, utterance, kind=intent.kind.value)

        if session is not None:
            session.mark_intent(intent.id)

        if intent.kind is IntentKind.CANCEL:
            if session is not None:
                session.cancel()
            self._emit(VoiceEventType.CANCELLED, utterance)
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.CANCELLED,
                message="voice session action cancelled by operator intent",
            )

        action = self.planner.plan(intent, context)
        if action is None:
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.NEEDS_CONTEXT,
                message="no bounded CyberCore action could be planned from this utterance",
            )

        continuity = self.howedo.evaluate(action, context)
        self._emit(
            VoiceEventType.CONTINUITY_EVALUATED,
            utterance,
            decision=continuity.decision.value,
        )
        if continuity.decision is not ContinuityDecision.CONTINUE:
            self._emit(
                VoiceEventType.ACTION_BLOCKED,
                utterance,
                reason="continuity",
            )
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.BLOCKED_CONTINUITY,
                message=continuity.reason,
                action=action,
                continuity_decision=continuity.decision.value,
            )

        governance = self.oathdo.evaluate(action, context)
        self._emit(
            VoiceEventType.GOVERNANCE_EVALUATED,
            utterance,
            decision=governance.decision.value,
        )
        if governance.decision is GovernanceDecision.DENY:
            self._emit(
                VoiceEventType.ACTION_BLOCKED,
                utterance,
                reason="governance",
            )
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.BLOCKED_GOVERNANCE,
                message=governance.reason,
                action=action,
                continuity_decision=continuity.decision.value,
                governance_decision=governance.decision.value,
            )

        if action.mutating and intent.kind is IntentKind.APPROVE:
            try:
                approval_intent = capture_voice_approval_intent(utterance, action)
            except ValueError as exc:
                return self._response(
                    utterance,
                    intent,
                    status=ResponseStatus.NEEDS_CONTEXT,
                    message=str(exc),
                    action=action,
                    continuity_decision=continuity.decision.value,
                    governance_decision=governance.decision.value,
                )
            self._emit(
                VoiceEventType.APPROVAL_INTENT_CAPTURED,
                utterance,
                approval_intent_id=approval_intent.id,
            )
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.APPROVAL_INTENT_CAPTURED,
                message=(
                    "voice approval intent captured; it is not execution authorization "
                    "until CyberCore verifies a matching plan-bound approval"
                ),
                action=action,
                continuity_decision=continuity.decision.value,
                governance_decision=governance.decision.value,
                approval_intent_id=approval_intent.id,
            )

        if governance.decision is GovernanceDecision.APPROVAL_REQUIRED:
            return self._response(
                utterance,
                intent,
                status=ResponseStatus.APPROVAL_REQUIRED,
                message=governance.reason,
                action=action,
                continuity_decision=continuity.decision.value,
                governance_decision=governance.decision.value,
            )

        if action.mutating:
            if not action.has_bound_plan:
                return self._response(
                    utterance,
                    intent,
                    status=ResponseStatus.NEEDS_CONTEXT,
                    message="mutating voice action requires an exact plan id and revision",
                    action=action,
                    continuity_decision=continuity.decision.value,
                    governance_decision=governance.decision.value,
                )
            approval = self.approval_verifier.verify(action)
            if not approval.authorized:
                return self._response(
                    utterance,
                    intent,
                    status=ResponseStatus.APPROVAL_REQUIRED,
                    message=approval.reason,
                    action=action,
                    continuity_decision=continuity.decision.value,
                    governance_decision=governance.decision.value,
                )
            approval_id = approval.approval_id
        else:
            approval_id = None

        self._emit(VoiceEventType.ACTION_READY, utterance, operation=action.operation)
        return self._response(
            utterance,
            intent,
            status=ResponseStatus.READY,
            message="bounded CyberCore action is ready for the existing execution boundary",
            action=action,
            continuity_decision=continuity.decision.value,
            governance_decision=governance.decision.value,
            approval_id=approval_id,
        )
