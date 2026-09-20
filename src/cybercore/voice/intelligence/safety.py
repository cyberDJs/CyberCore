from __future__ import annotations

import re
import unicodedata

from cybercore.voice.models import IntentKind, Utterance, VoiceContext, VoiceIntent


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^\w\s]", " ", asciiish)
    return " ".join(words_only.strip().split())


def _unquoted_clauses(text: str) -> tuple[str, ...]:
    unquoted = re.sub(r'["„“”][^"„“”\n]*["„“”]', " ", text)
    return tuple(part for part in re.split(r"[;.!?\n]+", unquoted) if part.strip())


class SafetyIntentGuard:
    _CANCEL_MARKERS = frozenset(
        {"cancel", "stop", "abort", "zrus", "zrusit", "zastav", "storno", "stornuj"}
    )
    _CANCEL_NEGATION = re.compile(
        r"\b(?:never|cannot|do not|does not|did not|should not|must not|can not|could not|"
        r"would not|will not|don t|doesn t|didn t|shouldn t|mustn t|can t|couldn t|"
        r"wouldn t|won t|nezrus|nezastav|nezastavuj)\b"
    )
    _CANCEL_COMMAND_PREFIX = re.compile(
        r"^(?:"
        r"(?:please|prosim|hey|cyber|ok|okay)"
        r"|(?:(?:can|could|would|will)\s+you(?:\s+(?:please|maybe))?)"
        r"|(?:i\s+(?:need|want)\s+you\s+to)"
        r"|(?:i\s+would\s+like\s+you\s+to)"
        r"|(?:(?:muzes|mohl\s+bys|mohla\s+bys)(?:\s+prosim)?)"
        r")$"
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
    def _is_cancel_command(cls, raw_text: str) -> bool:
        for raw_clause in _unquoted_clauses(raw_text):
            clause = _normalize(raw_clause)
            tokens = clause.split()
            if cls._CANCEL_MENTION.search(clause):
                continue
            for index, token in enumerate(tokens):
                if token not in cls._CANCEL_MARKERS:
                    continue
                local_prefix = " ".join(tokens[max(0, index - 6) : index])
                if cls._CANCEL_NEGATION.search(local_prefix):
                    continue
                if index == 0 or cls._CANCEL_COMMAND_PREFIX.fullmatch(local_prefix):
                    return True
        return False

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent | None:
        text = _normalize(utterance.text)
        kind: IntentKind | None = None
        if self._is_cancel_command(utterance.text):
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
