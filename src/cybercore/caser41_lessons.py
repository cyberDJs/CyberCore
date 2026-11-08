"""CASER operational lesson eligibility checks.

Lessons are untrusted evidence, never policy, authority or an automatic
instruction to change source code or execute external actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class LessonRecord:
    lesson_id: str
    project: str
    context_fingerprint: str
    root_cause: str
    guardrail: str
    evidence_refs: tuple[str, ...]
    confidence: float
    last_verified_at: datetime
    revalidate_after: datetime
    contradicted: bool = False


@dataclass(frozen=True)
class LessonVerdict:
    status: str
    reason: str


def assess_lesson(
    lesson: LessonRecord,
    *,
    project: str,
    context_fingerprint: str,
    now: datetime,
) -> LessonVerdict:
    """Gate lesson reuse; ELIGIBLE_FOR_REVIEW is never permission to execute."""
    if not isinstance(lesson, LessonRecord):
        return LessonVerdict("REJECTED", "INVALID_LESSON_SHAPE")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in (
            lesson.lesson_id,
            lesson.project,
            lesson.context_fingerprint,
            lesson.root_cause,
            lesson.guardrail,
            project,
            context_fingerprint,
        )
    ):
        return LessonVerdict("REJECTED", "INVALID_LESSON_SHAPE")
    if (
        not isinstance(lesson.evidence_refs, tuple)
        or not lesson.evidence_refs
        or any(not isinstance(ref, str) or not ref.strip() for ref in lesson.evidence_refs)
    ):
        return LessonVerdict("REJECTED", "MISSING_OR_INVALID_EVIDENCE")
    if (
        not isinstance(lesson.confidence, (float, int))
        or isinstance(lesson.confidence, bool)
        or not 0 <= lesson.confidence <= 1
    ):
        return LessonVerdict("REJECTED", "INVALID_CONFIDENCE")
    if not isinstance(lesson.contradicted, bool):
        return LessonVerdict("REJECTED", "INVALID_LESSON_SHAPE")
    timestamps = (lesson.last_verified_at, lesson.revalidate_after, now)
    try:
        if any(
            not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None
            for value in timestamps
        ):
            return LessonVerdict("REJECTED", "INVALID_TIMESTAMPS")
        verified_utc = lesson.last_verified_at.astimezone(timezone.utc)
        expiry_utc = lesson.revalidate_after.astimezone(timezone.utc)
        now_utc = now.astimezone(timezone.utc)
    except (OverflowError, ValueError, TypeError):
        return LessonVerdict("REJECTED", "INVALID_TIMESTAMPS")
    if verified_utc > expiry_utc or verified_utc > now_utc:
        return LessonVerdict("REJECTED", "INVALID_TIMESTAMPS")
    if lesson.contradicted:
        return LessonVerdict("REVALIDATION_REQUIRED", "CONTRADICTORY_EVIDENCE")
    if lesson.project != project or lesson.context_fingerprint != context_fingerprint:
        return LessonVerdict("REVALIDATION_REQUIRED", "CONTEXT_CHANGED")
    if now_utc >= expiry_utc:
        return LessonVerdict("REVALIDATION_REQUIRED", "LESSON_EXPIRED")
    if lesson.confidence < 0.8:
        return LessonVerdict("REVALIDATION_REQUIRED", "LOW_CONFIDENCE")
    return LessonVerdict("ELIGIBLE_FOR_REVIEW", "CURRENT_EVIDENCE_CANDIDATE")
