from dataclasses import replace
from datetime import datetime, timedelta, timezone, tzinfo

from cybercore.caser41_evidence_preflight import EvidenceCandidate, inspect_candidates

SHA = "a" * 40
NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)


def _record() -> EvidenceCandidate:
    return EvidenceCandidate(
        provider="github",
        run_id="123",
        attempt=1,
        repository="cyberDJs/CyberCore",
        commit_sha=SHA,
        conclusion="success",
        occurred_at=NOW,
        digest="b" * 64,
        source_ref="github:actions/123",
    )


def _inspect(*records: EvidenceCandidate):
    return inspect_candidates(tuple(records), repository="cyberDJs/CyberCore", commit_sha=SHA)


def test_valid_shape_never_claims_trusted_evidence() -> None:
    assert _inspect(_record()).status == "CANDIDATE_ONLY"
    assert _inspect(_record()).reason == "PROVIDER_AND_ANCHOR_UNVERIFIED"


def test_source_drift_and_duplicate_attempts_are_blocked() -> None:
    assert _inspect(replace(_record(), commit_sha="c" * 40)).reason == "SOURCE_DRIFT"
    assert _inspect(_record(), _record()).reason == "DUPLICATE_ATTEMPT"


def test_distinct_attempts_remain_distinct_candidates() -> None:
    result = _inspect(_record(), replace(_record(), attempt=2, conclusion="failure"))
    assert result.status == "CANDIDATE_ONLY"


def test_missing_batch_or_invalid_identity_fails_closed() -> None:
    assert _inspect().reason == "INVALID_BATCH"
    assert _inspect(replace(_record(), provider=None)).reason == "INVALID_IDENTITY"
    assert _inspect(replace(_record(), attempt=True)).reason == "INVALID_ATTEMPT"


def test_bad_outcome_or_digest_fails_closed() -> None:
    assert _inspect(replace(_record(), conclusion="pending")).reason == "INVALID_CONCLUSION"
    assert _inspect(replace(_record(), digest="forged")).reason == "INVALID_DIGEST"


def test_invalid_timestamp_fails_closed() -> None:
    assert _inspect(replace(_record(), occurred_at=NOW.replace(tzinfo=None))).reason == (
        "INVALID_TIMESTAMP"
    )
    boundary = datetime.min.replace(tzinfo=timezone(timedelta(hours=14)))
    assert _inspect(replace(_record(), occurred_at=boundary)).reason == "INVALID_TIMESTAMP"


class BrokenOffset(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta:
        raise RuntimeError("untrusted timezone failure")

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)


def test_malformed_expected_repository_is_rejected() -> None:
    for invalid in ("evil\\nrepo", "bad\\x00repo", "no-slash", "a/b/c"):
        verdict = inspect_candidates(
            (replace(_record(), repository=invalid),),
            repository=invalid,
            commit_sha=SHA,
        )
        assert verdict.reason == "INVALID_BATCH"


def test_malformed_record_repository_is_rejected() -> None:
    assert _inspect(replace(_record(), repository="evil\\nrepo")).reason == (
        "INVALID_SOURCE_IDENTITY"
    )
    assert _inspect(replace(_record(), repository=None)).reason == ("INVALID_SOURCE_IDENTITY")


def test_hostile_timezone_exception_is_blocked() -> None:
    stamp = NOW.replace(tzinfo=BrokenOffset())
    assert _inspect(replace(_record(), occurred_at=stamp)).reason == "INVALID_TIMESTAMP"


def test_malformed_record_sha_and_conclusion_are_blocked() -> None:
    assert _inspect(replace(_record(), commit_sha=None)).reason == ("INVALID_SOURCE_IDENTITY")
    assert _inspect(replace(_record(), conclusion=None)).reason == ("INVALID_CONCLUSION")
