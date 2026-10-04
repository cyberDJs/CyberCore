from __future__ import annotations

import re
import unicodedata

from cybercore.voice.models import IntentKind, Utterance, VoiceContext, VoiceIntent


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    words_only = re.sub(r"[^\w\s]", " ", asciiish)
    return " ".join(words_only.strip().split())


def _unquoted_clauses_with_delimiters(text: str) -> tuple[tuple[str, str], ...]:
    unquoted = re.sub(r'["„“”][^"„“”\n]*["„“”]', " ", text)
    unquoted = re.sub(r"(?<!\w)'[^'\n]*'(?!\w)|‘[^’\n]*’", " ", unquoted)
    return tuple(
        (match.group(1), match.group(2))
        for match in re.finditer(r"([^;.!?\n]+)([;.!?\n]+|$)", unquoted)
        if match.group(1).strip()
    )


class SafetyIntentGuard:
    _CANCEL_MARKERS = frozenset(
        {"cancel", "stop", "abort", "zrus", "zrusit", "zastav", "storno", "stornuj"}
    )
    _CANCEL_NEGATION = re.compile(
        r"\b(?:not|never|cannot|don t|doesn t|didn t|shouldn t|mustn t|can t|couldn t|"
        r"wouldn t|won t|nezrus|nezastav|nezastavuj)\b"
    )
    _CANCEL_MODIFIERS = frozenset(
        {
            "please",
            "prosim",
            "just",
            "quickly",
            "kindly",
            "simply",
            "maybe",
            "now",
            "right",
            "immediately",
            "hned",
            "nyni",
            "ted",
        }
    )
    _CANCEL_DISCOURSE = frozenset({"hey", "cyber", "ok", "okay"})
    _CANCEL_COORDINATORS = frozenset({"and", "or"})
    _CANCEL_MODAL_REQUESTS = frozenset({"can", "could", "would", "will"})
    _CANCEL_DESCRIPTION_COPULAS = frozenset(
        {"is", "are", "was", "were", "means", "mean", "refers", "represents", "equals"}
    )
    _CANCEL_CONDITION_WORDS = frozenset({"if", "when", "unless"})
    _CANCEL_REASON_CLAUSE_WORDS = frozenset({"because", "since"})
    _CANCEL_CONDITION_AUXILIARIES = frozenset(
        {"am", "are", "is", "was", "were", "m", "re", "s", "has", "have", "had"}
    )
    _CANCEL_SIMPLE_PRESENT_PREDICATES = frozenset(
        {
            "recover",
            "recovers",
            "finish",
            "finishes",
            "complete",
            "completes",
            "end",
            "ends",
            "fail",
            "fails",
            "begin",
            "begins",
            "resume",
            "resumes",
            "return",
            "returns",
            "reconnect",
            "reconnects",
            "disconnect",
            "disconnects",
        }
    )
    _CANCEL_MATRIX_TAIL_BLOCKERS = frozenset(
        {
            "am",
            "are",
            "is",
            "was",
            "were",
            "has",
            "have",
            "had",
            "do",
            "does",
            "did",
            "can",
            "could",
            "would",
            "will",
            "should",
            "must",
            "may",
            "might",
        }
    )
    _CANCEL_NOUN_MODIFIERS = frozenset({"emergency"})
    _CANCEL_NOUN_HEADS = frozenset(
        {"button", "icon", "indicator", "key", "label", "light", "message", "sign"}
    )
    _CANCEL_IMPERATIVE_OBJECT_STARTERS = frozenset(
        {
            "all",
            "current",
            "every",
            "her",
            "him",
            "it",
            "me",
            "that",
            "the",
            "them",
            "this",
            "to",
            "us",
            "whatever",
            "whichever",
            "whoever",
        }
    )
    _CANCEL_NEGATIVE_OBJECT_STARTERS = frozenset(
        {
            "neither",
            "never",
            "no",
            "nobody",
            "none",
            "not",
            "nothing",
            "nowhere",
            "nic",
            "niceho",
            "nicemu",
            "nicim",
            "nikde",
            "nikdo",
            "nikoho",
            "nikomu",
            "nikym",
            "zadna",
            "zadne",
            "zadneho",
            "zadnem",
            "zadnemu",
            "zadni",
            "zadnim",
            "zadnou",
            "zadny",
            "zadnych",
            "zadnym",
            "zadnymi",
        }
    )
    _AUTHORITY_INTERROGATIVE_TAILS = frozenset(
        {
            "how",
            "what",
            "when",
            "where",
            "which",
            "who",
            "whom",
            "whose",
            "why",
            "ci",
            "ciho",
            "co",
            "ceho",
            "cemu",
            "cim",
            "jak",
            "jaka",
            "jake",
            "jakeho",
            "jakemu",
            "jaky",
            "jakym",
            "jakymi",
            "kde",
            "kdo",
            "kdy",
            "koho",
            "kolik",
            "kolika",
            "komu",
            "ktera",
            "ktere",
            "ktereho",
            "kteremu",
            "kteri",
            "kterou",
            "ktery",
            "kterych",
            "kterym",
            "kterymi",
            "kym",
            "proc",
        }
    )
    _CANCEL_SUBJECT_CLAUSE_DELIMITERS = frozenset({"hned", "immediately", "now", "nyni", "ted"})
    _AUTHORITY_DESCRIPTION_MODALS = frozenset(
        {"can", "could", "may", "might", "must", "should", "will", "would"}
    )
    _AUTHORITY_DESCRIPTION_PERFECT_AUXILIARIES = frozenset({"had", "has", "have"})
    _CANCEL_CONDITION_DESCRIPTIVE_PREDICATES = frozenset(
        {
            "called",
            "captioned",
            "displaying",
            "labeled",
            "labelled",
            "marked",
            "named",
            "showing",
            "titled",
        }
    )
    _CANCEL_CONDITION_TRAILING_BLOCKERS = frozenset(
        {
            "i",
            "you",
            "we",
            "they",
            "he",
            "she",
            "it",
            "can",
            "could",
            "would",
            "will",
            "should",
            "must",
            "may",
            "might",
        }
    )
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
    _CANCEL_NEGATION_SCOPE_ADVERBS = frozenset({"again", "ever"})
    _CANCEL_NEGATION_SCOPE_PRODUCTIVE_ADVERB_ANCHORS = frozenset({"ever"})
    _CANCEL_NEGATION_SCOPE_ASIDES = frozenset(
        {
            ("at", "all", "costs"),
            ("for", "no", "reason"),
            ("on", "any", "account"),
            ("under", "any", "circumstances"),
            ("under", "these", "circumstances"),
            ("without", "exception"),
        }
    )
    _CANCEL_MENTION = re.compile(
        r"\b(?:explain|define|meaning|mean|means|word|term|phrase|mention|mentioned|"
        r"vysvetli|definuj|znamena|slovo|vyraz)\b"
    )
    _APPROVE_MARKERS = frozenset({"approve", "schvaluju", "schvaluji", "souhlasim"})
    _APPROVE_PREFIXES = frozenset({"ano", "jo", "yes", "please", "prosim"})
    _APPROVE_PHRASES = frozenset({"jo udelej to", "ano proved to", "yes do it"})
    _EXECUTE_MARKERS = frozenset({"execute", "apply", "run", "proved", "spust", "udelej"})
    _EXECUTE_PREFIXES = frozenset({"please", "prosim"})

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
        if len(tokens) < 3 or tokens[0] not in cls._CANCEL_CONDITION_WORDS:
            return False
        auxiliary_index = next(
            (
                index
                for index, token in enumerate(tokens[2:], start=2)
                if token in cls._CANCEL_CONDITION_AUXILIARIES
            ),
            None,
        )
        if auxiliary_index is None:
            subject = tokens[1:-1]
            predicate = tokens[-1]
            if not subject:
                return False
            if predicate in cls._CANCEL_REPORTING_VERBS:
                return False
            return predicate in cls._CANCEL_SIMPLE_PRESENT_PREDICATES
        if auxiliary_index >= len(tokens) - 1:
            return False
        subject = tokens[1:auxiliary_index]
        predicate = tokens[auxiliary_index + 1 :]
        if not subject or not predicate:
            return False
        if predicate[-1] == "to":
            return False
        if predicate[-1] in cls._CANCEL_REPORTING_VERBS:
            return False
        if predicate[-1] in cls._CANCEL_CONDITION_DESCRIPTIVE_PREDICATES:
            return False
        if predicate[-1] in cls._CANCEL_CONDITION_TRAILING_BLOCKERS:
            return False
        return True

    @classmethod
    def _continues_negation_scope(cls, tokens: list[str]) -> bool:
        allowed = (
            cls._CANCEL_NEGATION_SCOPE_AUXILIARIES
            | cls._CANCEL_NEGATION_SCOPE_ADVERBS
            | cls._CANCEL_MODIFIERS
            | cls._CANCEL_DISCOURSE
        )
        if all(token in allowed for token in tokens):
            return True
        return tuple(tokens) in cls._CANCEL_NEGATION_SCOPE_ASIDES

    @classmethod
    def _opens_negation_scope(cls, tokens: list[str]) -> bool:
        segment = " ".join(tokens)
        if not cls._CANCEL_NEGATION.search(segment):
            return False
        remainder = _normalize(cls._CANCEL_NEGATION.sub(" ", segment)).split()
        if cls._continues_negation_scope(remainder):
            return True
        has_productive_adverb_anchor = bool(
            set(remainder) & cls._CANCEL_NEGATION_SCOPE_PRODUCTIVE_ADVERB_ANCHORS
        )
        return has_productive_adverb_anchor and all(
            token.endswith("ly") or cls._continues_negation_scope([token]) for token in remainder
        )

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
        negative_subject_after_delimiter = (
            len(before_copula) >= 2
            and before_copula[0] in cls._CANCEL_SUBJECT_CLAUSE_DELIMITERS
            and before_copula[1] in cls._CANCEL_NEGATIVE_OBJECT_STARTERS
            and bool(tail[copula_index + 1 :])
        )
        if negative_subject_after_delimiter:
            return False
        if set(before_copula) & cls._CANCEL_CONDITION_WORDS:
            return False
        if set(before_copula) & cls._CANCEL_REASON_CLAUSE_WORDS:
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
    def _coordinated_markers_are_description(
        cls, tokens: list[str], marker_indexes: list[int]
    ) -> bool:
        if len(marker_indexes) < 2:
            return False
        first_marker = marker_indexes[0]
        prefix = tokens[:first_marker]
        if not prefix:
            return False
        if prefix[-1] not in (cls._CANCEL_REPORTING_VERBS | cls._CANCEL_DESCRIPTION_COPULAS):
            return False
        allowed_tail = cls._CANCEL_MARKERS | cls._CANCEL_COORDINATORS
        return all(token in allowed_tail for token in tokens[first_marker:])

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
    def _authority_marker_leads_description(cls, tokens: list[str], index: int) -> bool:
        tail = tokens[index + 1 :]
        reason_index = next(
            (
                position
                for position, token in enumerate(tail)
                if token in cls._CANCEL_REASON_CLAUSE_WORDS
            ),
            None,
        )
        if reason_index is not None:
            tail = tail[:reason_index]
        if not tail:
            return False
        relative_positions = [
            position
            for position, token in enumerate(tail)
            if token in cls._CANCEL_RELATIVE_PRONOUNS
        ]
        first_relative = relative_positions[0] if relative_positions else len(tail)
        matrix_tail = tail[:first_relative]

        if any(
            token in cls._AUTHORITY_DESCRIPTION_MODALS and "be" in matrix_tail[position + 1 :]
            for position, token in enumerate(matrix_tail)
        ):
            return True
        if any(
            token in cls._AUTHORITY_DESCRIPTION_PERFECT_AUXILIARIES
            and "been" in matrix_tail[position + 1 :]
            for position, token in enumerate(matrix_tail)
        ):
            return True

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
        relative_positions = [
            position
            for position, token in enumerate(before_copula)
            if token in cls._CANCEL_RELATIVE_PRONOUNS
        ]
        if relative_positions:
            relative_tail = before_copula[relative_positions[0] + 1 :]
            if any(
                (
                    token in cls._AUTHORITY_DESCRIPTION_MODALS
                    and "be" in relative_tail[position + 1 :]
                )
                for position, token in enumerate(relative_tail)
            ):
                return True
            if any(
                token in cls._AUTHORITY_DESCRIPTION_PERFECT_AUXILIARIES
                and "been" in relative_tail[position + 1 :]
                for position, token in enumerate(relative_tail)
            ):
                return True
            return any(
                token in cls._CANCEL_DESCRIPTION_COPULAS for token in tail[copula_index + 1 :]
            )
        if set(before_copula) & cls._CANCEL_FREE_RELATIVES:
            return False
        return True

    @classmethod
    def _condition_prefix_may_govern_marker(cls, tokens: list[str]) -> bool:
        if len(tokens) < 3 or tokens[0] not in cls._CANCEL_CONDITION_WORDS:
            return False
        auxiliary_index = next(
            (
                index
                for index, token in enumerate(tokens[2:], start=2)
                if token in cls._CANCEL_CONDITION_AUXILIARIES
            ),
            None,
        )
        if auxiliary_index is None:
            return False
        predicate = tokens[auxiliary_index + 1 :]
        return any(token.endswith("ing") for token in predicate)

    @classmethod
    def _cancel_marker_has_explicit_imperative_tail(cls, tokens: list[str], index: int) -> bool:
        tail = tokens[index + 1 :]
        if not tail:
            return False
        if tail[0] == "to":
            return False
        if tail[0] in cls._CANCEL_MODIFIERS:
            return True
        if tail[0] in cls._CANCEL_IMPERATIVE_OBJECT_STARTERS:
            return True
        return len(tail) == 2 and tail[1] in cls._CANCEL_MODIFIERS

    @classmethod
    def _cancel_marker_has_imperative_tail(
        cls,
        tokens: list[str],
        index: int,
        *,
        question_scope: bool = False,
    ) -> bool:
        if index > 0 and tokens[index - 1] in cls._CANCEL_NOUN_MODIFIERS:
            return False
        tail = tokens[index + 1 :]
        if not tail:
            return True
        semantic_tail = tail
        while semantic_tail and semantic_tail[0] in cls._CANCEL_MODIFIERS:
            semantic_tail = semantic_tail[1:]
        if question_scope and any(
            token in cls._AUTHORITY_INTERROGATIVE_TAILS for token in semantic_tail
        ):
            return False
        subject_auxiliary_index = next(
            (
                position
                for position, token in enumerate(tail[2:], start=2)
                if token in cls._CANCEL_CONDITION_AUXILIARIES
            ),
            None,
        )
        negative_starts_following_clause = (
            len(tail) >= 4
            and tail[0] in cls._CANCEL_SUBJECT_CLAUSE_DELIMITERS
            and tail[1] in cls._CANCEL_NEGATIVE_OBJECT_STARTERS
            and subject_auxiliary_index is not None
            and bool(tail[subject_auxiliary_index + 1 :])
        )
        if (
            semantic_tail
            and semantic_tail[0] in cls._CANCEL_NEGATIVE_OBJECT_STARTERS
            and not negative_starts_following_clause
        ):
            return False
        if tail[0] in cls._CANCEL_MATRIX_TAIL_BLOCKERS:
            return False
        if tail[0] in cls._CANCEL_NOUN_HEADS:
            return False
        if tail[0] in cls._CANCEL_MODIFIERS:
            return True
        if tail[0] in cls._CANCEL_IMPERATIVE_OBJECT_STARTERS:
            return True
        trailing_trimmed = list(tail)
        while trailing_trimmed and trailing_trimmed[-1] in cls._CANCEL_MODIFIERS:
            trailing_trimmed.pop()
        if trailing_trimmed and len(trailing_trimmed) < len(tail):
            return True
        if len(tail) == 1:
            return True
        return any(token in cls._CANCEL_CONDITION_WORDS for token in tail[1:])

    @classmethod
    def _authority_marker_has_safe_tail(cls, tokens: list[str], index: int) -> bool:
        semantic_tail = tokens[index + 1 :]
        while semantic_tail and semantic_tail[0] in cls._CANCEL_MODIFIERS:
            semantic_tail = semantic_tail[1:]
        if not semantic_tail:
            return True
        has_negative_object = any(
            token in cls._CANCEL_NEGATIVE_OBJECT_STARTERS for token in semantic_tail
        )
        has_verbal_negation = bool(cls._CANCEL_NEGATION.search(" ".join(semantic_tail)))
        has_interrogative_boundary = (
            semantic_tail[0] in cls._AUTHORITY_INTERROGATIVE_TAILS
            or semantic_tail[-1] in cls._AUTHORITY_INTERROGATIVE_TAILS
        )
        return (
            not has_negative_object
            and not has_verbal_negation
            and not has_interrogative_boundary
        )

    @classmethod
    def _is_bare_authority_question(
        cls,
        raw_clause: str,
        delimiter: str,
        markers: frozenset[str],
        prefixes: frozenset[str],
    ) -> bool:
        if "?" not in delimiter:
            return False
        tokens = _normalize(raw_clause).split()
        allowed_modifiers = prefixes | cls._CANCEL_MODIFIERS | cls._CANCEL_DISCOURSE
        while tokens and tokens[0] in allowed_modifiers:
            tokens = tokens[1:]
        while tokens and tokens[-1] in allowed_modifiers:
            tokens = tokens[:-1]
        return bool(tokens) and tokens[0] in markers

    @classmethod
    def _is_fixed_approval_phrase(cls, raw_text: str) -> bool:
        for raw_clause, delimiter in _unquoted_clauses_with_delimiters(raw_text):
            if "?" in delimiter:
                continue
            if _normalize(raw_clause) in cls._APPROVE_PHRASES:
                return True
        return False

    @classmethod
    def _is_authority_command(
        cls,
        raw_text: str,
        markers: frozenset[str],
        prefixes: frozenset[str],
    ) -> bool:
        for raw_clause, delimiter in _unquoted_clauses_with_delimiters(raw_text):
            if cls._is_bare_authority_question(raw_clause, delimiter, markers, prefixes):
                continue
            tokens = _normalize(raw_clause).split()
            if not tokens:
                continue
            if cls._CANCEL_MENTION.search(" ".join(tokens)):
                continue

            remaining = list(tokens)
            while remaining and remaining[0] in prefixes:
                remaining.pop(0)
            marker_index = len(tokens) - len(remaining)
            if not remaining or remaining[0] not in markers:
                continue
            if cls._CANCEL_NEGATION.search(" ".join(tokens[:marker_index])):
                continue
            if cls._authority_marker_leads_description(tokens, marker_index):
                continue
            if not cls._authority_marker_has_safe_tail(tokens, marker_index):
                continue
            return True
        return False

    @classmethod
    def _is_cancel_command(cls, raw_text: str) -> bool:
        cancel_detected = False
        for raw_clause, delimiter in _unquoted_clauses_with_delimiters(raw_text):
            if cls._is_bare_authority_question(
                raw_clause,
                delimiter,
                cls._CANCEL_MARKERS,
                cls._CANCEL_MODIFIERS | cls._CANCEL_DISCOURSE,
            ):
                continue
            raw_segments = [segment for segment in raw_clause.split(",") if _normalize(segment)]
            if (
                "?" in delimiter
                and raw_segments
                and cls._is_bare_authority_question(
                    raw_segments[-1],
                    delimiter,
                    cls._CANCEL_MARKERS,
                    cls._CANCEL_MODIFIERS | cls._CANCEL_DISCOURSE,
                )
            ):
                raw_segments = raw_segments[:-1]
                if not raw_segments:
                    continue
                raw_clause = ",".join(raw_segments)
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
            if cls._coordinated_markers_are_description(clause_tokens, clause_markers):
                continue
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
                    elif pending_negation and not cls._continues_negation_scope(tokens):
                        pending_negation = False
                    continue
                if cls._CANCEL_MENTION.search(segment):
                    continue

                for index in markers:
                    prefix_tokens = tokens[:index]
                    local_prefix_tokens = prefix_tokens[-8:]
                    local_prefix = " ".join(local_prefix_tokens)
                    if pending_negation:
                        cancel_detected = False
                        continue
                    if cls._CANCEL_NEGATION.search(local_prefix):
                        cancel_detected = False
                        continue
                    if cls._marker_leads_description(tokens, index):
                        continue
                    if not cls._cancel_marker_has_imperative_tail(
                        tokens,
                        index,
                        question_scope="?" in delimiter,
                    ):
                        continue
                    command_prefix = cls._is_command_prefix(local_prefix_tokens)
                    condition_prefix = cls._is_condition_command_prefix(prefix_tokens)
                    if (
                        condition_prefix
                        and cls._condition_prefix_may_govern_marker(prefix_tokens)
                        and not cls._cancel_marker_has_explicit_imperative_tail(tokens, index)
                    ):
                        continue
                    if command_prefix or condition_prefix:
                        cancel_detected = True
        return cancel_detected

    def compile(self, utterance: Utterance, context: VoiceContext) -> VoiceIntent | None:
        kind: IntentKind | None = None
        if self._is_cancel_command(utterance.text):
            kind = IntentKind.CANCEL
        elif self._is_fixed_approval_phrase(utterance.text) or self._is_authority_command(
            utterance.text,
            self._APPROVE_MARKERS,
            self._APPROVE_PREFIXES,
        ):
            kind = IntentKind.APPROVE
        elif self._is_authority_command(
            utterance.text,
            self._EXECUTE_MARKERS,
            self._EXECUTE_PREFIXES,
        ):
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
