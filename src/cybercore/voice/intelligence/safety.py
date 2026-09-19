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
    _CANCEL = re.compile(
        r"^(?:(?:hey|hele|ok|okay)\s+)?"
        r"(?:(?:please|prosim)\s+)?"
        r"(?:(?:(?:can|could|would|will)\s+you\s+(?:please\s+)?)"
        r"|(?:i\s+(?:need|want)\s+you\s+to\s+)"
        r"|(?:(?:muzes|mohl\s+bys|mohla\s+bys)\s+(?:prosim\s+)?))?"
        r"(?:cancel|stop|abort|zrus|zrusit|zastav|storno|stornuj)"
        r"(?:\s+.*)?$"
    )
    _APPROVE = re.compile(
        r"^(?:(?:ano|jo|yes)\s+)?(?:approve|schvaluju|schvaluji|souhlasim)(?:\s+.*)?$"
    )
    _APPROVE_PHRASES = frozenset({"jo udelej to", "ano proved to", "yes do it"})
    _EXECUTE = re.compile(
        r"^(?:(?:please|prosim)\s+)?(?:execute|apply|run|proved|spust|udelej)(?:\s+.*)?$"
    )

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent | None:
        text = _normalize(utterance.text)
        kind: IntentKind | None = None
        if self._CANCEL.fullmatch(text):
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
