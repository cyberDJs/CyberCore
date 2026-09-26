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
        r"\b(?:not|never|cannot|don t|doesn t|didn t|shouldn t|mustn t|can t|couldn t|"
        r"wouldn t|won t|nezrus|nezastav|nezastavuj)\b"
    )
    _CANCEL_MODIFIERS = frozenset(
        {"please", "prosim", "just", "quickly", "kindly", "simply", "maybe", "now", "immediately"}
    )
    _CANCEL_DISCOURSE = frozenset({"hey", "cyber", "ok", "okay"})
    _CANCEL_MODAL_REQUESTS = frozenset({"can", "could", "would", "will"})
    _CANCEL_DESCRIPTION_COPULAS = frozenset(
        {"is", "are", "was", "were", "means", "mean", "refers", "represents", "equals"}
    )
    _CANCEL_CONDITION_WORDS = frozenset({"if", "when", "unless"})
    _CANCEL_CONDITION_AUXILIARIES = frozenset({"am", "are", "is", "was", "were", "m", "re", "s"})
    _CANCEL_REPORTING_VERBS = frozenset(
        {
            "say",
            "says",
            "saying",
            "mean",
            "means",
            "meaning",
            "spell",
            "spells",
            "spelling",
            "discuss",
            "discusses",
            "discussing",
            "mention",
            "mentions",
            "mentioning",
            "quote",
            "quotes",
            "quoting",
            "define",
            "defines",
            "defining",
            "explain",
            "explains",
            "explaining",
        }
    )
    _CANCEL_RELATIVE_PRONOUNS = frozenset({"that", "which", "who"})
    _CANCEL_FREE_RELATIVES = frozenset({"whatever", "whichever", "whoever"})
    _CANCEL_NEGATION_SCOPE_AUXILIARIES = frozenset(
        {"i", "you", "we", "do", "does", "did", "should", "must", "can", "could", "would", "will"}
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
    def _is_command_prefix(cls, tokens: list[str]) -> bool:
        if not tokens:
            return True

        remaining = list(tokens)
        while remaining and (
            remaining[0] in cls._CANCEL_DISCOURSE or remaining[0] in cls._CANCEL_MODIFIERS
        ):
            remaining.pop(0)
        if not remaining:
            return True

        if (
            len(remaining) >= 2
            and remaining[0] in cls._CANCEL_MODAL_REQUESTS
            and remaining[1] == "you"
        ):
            remaining = remaining[2:]
            while remaining and remaining[0] in cls._CANCEL_MODIFIERS:
                remaining.pop(0)
            return not remaining

        request_prefixes = (
            ("i", "need", "you", "to"),
            ("i", "want", "you", "to"),
            ("i", "would", "like", "you", "to"),
            ("muzes",),
            ("mohl", "bys"),
            ("mohla", "bys"),
        )
        for prefix in request_prefixes:
            if tuple(remaining[: len(prefix)]) != prefix:
                continue
            tail = remaining[len(prefix) :]
            while tail and tail[0] in cls._CANCEL_MODIFIERS:
                tail = tail[1:]
            return not tail
        return False

    @classmethod
    def _is_condition_command_prefix(cls, tokens: list[str]) -> bool:
        if len(tokens) < 4 or tokens[0] not in cls._CANCEL_CONDITION_WORDS:
            return False
        auxiliary_index = next(
            (
                index
                for index, token in enumerate(tokens[2:], start=2)
                if token in cls._CANCEL_CONDITION_AUXILIARIES
            ),
            None,
        )
        if auxiliary_index is None or auxiliary_index >= len(tokens) - 1:
            return False
        subject = tokens[1:auxiliary_index]
        predicate = tokens[auxiliary_index + 1 :]
        if not subject or not predicate:
            return False
        if predicate[-1] == "to":
            return False
        if predicate[-1] in cls._CANCEL_REPORTING_VERBS:
            return False
        if predicate[-1] in {"i", "you", "we", "they", "he", "she", "it"}:
            if len(predicate) == 1 or predicate[-2] not in {
                "for",
                "to",
                "with",
                "about",
                "from",
                "of",
                "by",
                "at",
                "on",
                "in",
            }:
                return False
        return True

    @classmethod
    def _opens_negation_scope(cls, tokens: list[str]) -> bool:
        segment = " ".join(tokens)
        if not cls._CANCEL_NEGATION.search(segment):
            return False
        remainder = _normalize(cls._CANCEL_NEGATION.sub(" ", segment)).split()
        allowed = (
            cls._CANCEL_NEGATION_SCOPE_AUXILIARIES | cls._CANCEL_MODIFIERS | cls._CANCEL_DISCOURSE
        )
        return all(token in allowed for token in remainder)

    @classmethod
    def _marker_leads_description(cls, tokens: list[str], index: int) -> bool:
        if index < 0 or index >= len(tokens) or len(tokens[index:]) < 2:
            return False
        if index > 0 and not (
            cls._is_command_prefix(tokens[:index])
            or cls._is_condition_command_prefix(tokens[:index])
        ):
            return False
        tail = tokens[index + 1 :]
        copula_index = next(
            (
                position
                for position, token in enumerate(tail)
                if token in cls._CANCEL_DESCRIPTION_COPULAS
            ),
            None,
        )
        if copula_index is None:
            return False
        before_copula = tail[:copula_index]
        if set(before_copula) & cls._CANCEL_CONDITION_WORDS:
            return False
        if set(before_copula) & cls._CANCEL_FREE_RELATIVES:
            return False
        relative_positions = [
            position
            for position, token in enumerate(before_copula)
            if token in cls._CANCEL_RELATIVE_PRONOUNS
        ]
        if relative_positions:
            return relative_positions[0] == 0
        return True

    @classmethod
    def _nonrestrictive_description_prefix_length(cls, raw_segments: list[str]) -> int:
        if len(raw_segments) < 3:
            return 0

        first_tokens = _normalize(raw_segments[0]).split()
        relative_tokens = _normalize(raw_segments[1]).split()
        tail_tokens = _normalize(raw_segments[2]).split()
        if not first_tokens or not relative_tokens or not tail_tokens:
            return 0

        marker_indexes = [
            index for index, token in enumerate(first_tokens) if token in cls._CANCEL_MARKERS
        ]
        if len(marker_indexes) != 1:
            return 0
        marker_index = marker_indexes[0]
        if marker_index != len(first_tokens) - 1:
            return 0
        if not cls._is_command_prefix(first_tokens[:marker_index]):
            return 0
        if relative_tokens[0] not in cls._CANCEL_RELATIVE_PRONOUNS:
            return 0
        if not any(token in cls._CANCEL_DESCRIPTION_COPULAS for token in relative_tokens):
            return 0
        if tail_tokens[0] not in cls._CANCEL_DESCRIPTION_COPULAS:
            return 0
        return 3

    @classmethod
    def _is_cancel_command(cls, raw_text: str) -> bool:
        for raw_clause in _unquoted_clauses(raw_text):
            raw_segments = [segment for segment in raw_clause.split(",") if _normalize(segment)]
            description_prefix_length = cls._nonrestrictive_description_prefix_length(raw_segments)
            if description_prefix_length:
                raw_segments = raw_segments[description_prefix_length:]
                if not raw_segments:
                    continue
                raw_clause = ",".join(raw_segments)

            clause_tokens = _normalize(raw_clause).split()
            clause_markers = [
                index for index, token in enumerate(clause_tokens) if token in cls._CANCEL_MARKERS
            ]
            if len(clause_markers) == 1 and cls._marker_leads_description(
                clause_tokens, clause_markers[0]
            ):
                continue

            pending_negation = False
            for raw_segment in raw_clause.split(","):
                segment = _normalize(raw_segment)
                tokens = segment.split()
                if not tokens:
                    continue

                markers = [
                    index for index, token in enumerate(tokens) if token in cls._CANCEL_MARKERS
                ]
                if not markers:
                    if cls._opens_negation_scope(tokens):
                        pending_negation = True
                    continue
                if cls._CANCEL_MENTION.search(segment):
                    continue

                for index in markers:
                    local_prefix_tokens = tokens[max(0, index - 8) : index]
                    local_prefix = " ".join(local_prefix_tokens)
                    if pending_negation:
                        pending_negation = False
                        continue
                    if cls._CANCEL_NEGATION.search(local_prefix):
                        continue
                    if cls._marker_leads_description(tokens, index):
                        continue
                    if cls._is_command_prefix(
                        local_prefix_tokens
                    ) or cls._is_condition_command_prefix(local_prefix_tokens):
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
