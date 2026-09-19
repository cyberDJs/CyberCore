from __future__ import annotations

import re
import unicodedata

from cybercore.voice.models import IntentKind, Utterance, VoiceContext, VoiceIntent


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^\w\s]", " ", asciiish)
    return " ".join(words_only.strip().split())


class SafetyIntentGuard:
    _CANCEL_MARKERS = frozenset(
        {"cancel", "stop", "abort", "zrus", "zrusit", "zastav", "storno", "stornuj"}
    )
    _CANCEL_NEGATION = re.compile(
        r"\b(?:do not|don t|dont|never|please do not|prosim nezrus|nezrus|nezastav)\b"
    )
    _CANCEL_MENTION = re.compile(
        r"\b(?:explain|define|meaning|mean|means|word|term|phrase|mention|mentioned|"
        r"vysvetli|definuj|znamena|slovo|vyraz)\b"
    )
    _APPROVE = re.compile(
        r"^(?:(?:ano|jo|yes)\s+)?(?:approve|schvaluju|schvaluji|souhlasim)(?:\s+.*)?$"
    )
    _APPROVE_PHRASES = frozenset({"jo udelej to", "ano proved to", "yes do it"})
    _EXECUTE = re.compile(
        r"^(?:(?:please|prosim)\s+)?(?:execute|apply|run|proved|spust|udelej)(?:\s+.*)?$"
    )

    @classmethod
    def _is_cancel_command(cls, text: str) -> bool:
        tokens = set(text.split())
        if not (tokens & cls._CANCEL_MARKERS):
            return False
        if cls._CANCEL_NEGATION.search(text):
            return False
        if cls._CANCEL_MENTION.search(text):
            return False
        return True

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent | None:
        text = _normalize(utterance.text)
        kind: IntentKind | None = None
        if self._is_cancel_command(text):
            kind = IntentKind.CANCEL
        elif text in self._APPROVE_PHRASES or self._APPROVE.fullmatch(text):
            kind = IntentKind.APPROVE
        elif self._EXECUTE.fullmatch(text):
            kind = IntentKind.EXECUTE
        if kind is None:
            return None
        return VoiceIntent(
            id=f"intent:{utterance.id}",
            utterance_id=utterance.id,
            kind=kind,
            operation=kind.value,
            target=context.references.get("target"),
            confidence=1.0,
        )

