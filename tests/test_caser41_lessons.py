from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cybercore.caser41_lessons import LessonRecord, assess_lesson

NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


def _lesson() -> LessonRecord:
    return LessonRecord(
        lesson_id="ruff-retry",
        project="cyberDJs/CyberCore",
        context_fingerprint="python-ruff-ci-v1",
        root_cause="Formatting was not checked before pushing",
        guardrail="Run deterministic Ruff format check before PR",
        evidence_refs=("github:pr/137",),
        confidence=0.95,
        last_verified_at=NOW - timedelta(days=2),
        revalidate_after=NOW + timedelta(days=14),
    )


def _check(lesson: LessonRecord, *, context: str = "python-ruff-ci-v1") -> str:
    return assess_lesson(
        lesson,
        project="cyberDJs/CyberCore",
        context_fingerprint=context,
        now=NOW,
    ).reason


def test_current_lesson_is_only_eligible_for_review() -> None:
    decision = assess_lesson(
        _lesson(),
        project="cyberDJs/CyberCore",
        context_fingerprint="python-ruff-ci-v1",
        now=NOW,
    )
    assert decision.status == "ELIGIBLE_FOR_REVIEW"


def test_expired_context_change_and_contradictions_require_revalidation() -> None:
    assert _check(replace(_lesson(), revalidate_after=NOW)) == "LESSON_EXPIRED"
    assert _check(_lesson(), context="python-ruff-ci-v2") == "CONTEXT_CHANGED"
    assert _check(replace(_lesson(), contradicted=True)) == "CONTRADICTORY_EVIDENCE"


def test_low_confidence_and_missing_evidence_never_reused() -> None:
    assert _check(replace(_lesson(), confidence=0.2)) == "LOW_CONFIDENCE"
    assert _check(replace(_lesson(), evidence_refs=())) == "MISSING_OR_INVALID_EVIDENCE"


def test_malformed_payload_fails_closed() -> None:
    assert _check(replace(_lesson(), confidence=float("nan"))) == "INVALID_CONFIDENCE"
    assert _check(replace(_lesson(), confidence=True)) == "INVALID_CONFIDENCE"
    assert _check(replace(_lesson(), project=None)) == "INVALID_LESSON_SHAPE"
    assert _check(replace(_lesson(), evidence_refs=(None,))) == "MISSING_OR_INVALID_EVIDENCE"
    assert _check(replace(_lesson(), contradicted="false")) == "INVALID_LESSON_SHAPE"


def test_naive_future_and_inverted_timestamps_fail_closed() -> None:
    naive = NOW.replace(tzinfo=None)
    assert _check(replace(_lesson(), last_verified_at=naive)) == "INVALID_TIMESTAMPS"
    assert _check(replace(_lesson(), last_verified_at=NOW + timedelta(days=1))) == (
        "INVALID_TIMESTAMPS"
    )
    assert _check(replace(_lesson(), revalidate_after=NOW - timedelta(days=3))) == (
        "INVALID_TIMESTAMPS"
    )


def test_dst_fall_back_fold_does_not_keep_expired_lesson_alive() -> None:
    eastern = ZoneInfo("America/New_York")
    expiry = datetime(2026, 11, 1, 1, 45, tzinfo=eastern, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=eastern, fold=1)
    original = _lesson()
    lesson = replace(
        original,
        last_verified_at=datetime(2026, 10, 31, 12, tzinfo=eastern),
        revalidate_after=expiry,
    )
    assert (
        assess_lesson(
            lesson,
            project=original.project,
            context_fingerprint=original.context_fingerprint,
            now=later,
        ).reason
        == "LESSON_EXPIRED"
    )


def test_dst_fold_future_verified_time_is_rejected() -> None:
    eastern = ZoneInfo("America/New_York")
    now = datetime(2026, 11, 1, 1, 45, tzinfo=eastern, fold=0)
    later = datetime(2026, 11, 1, 1, 15, tzinfo=eastern, fold=1)
    lesson = replace(
        _lesson(),
        last_verified_at=later,
        revalidate_after=later + timedelta(days=1),
    )
    assert (
        assess_lesson(
            lesson,
            project=lesson.project,
            context_fingerprint=lesson.context_fingerprint,
            now=now,
        ).reason
        == "INVALID_TIMESTAMPS"
    )


def test_utc_conversion_boundary_overflow_is_rejected() -> None:
    plus_fourteen = timezone(timedelta(hours=14))
    lesson = replace(
        _lesson(),
        last_verified_at=datetime.min.replace(tzinfo=plus_fourteen),
    )
    assert _check(lesson) == "INVALID_TIMESTAMPS"
