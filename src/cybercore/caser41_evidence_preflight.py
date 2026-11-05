"""Conservative read-only preflight for CASER provider evidence.

All input remains untrusted. A valid result is NOT an attestation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", re.ASCII)
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", re.ASCII)


@dataclass(frozen=True)
class EvidenceCandidate:
    provider: str
    run_id: str
    attempt: int
    repository: str
    commit_sha: str
    conclusion: str
    occurred_at: datetime
    digest: str
    source_ref: str


@dataclass(frozen=True)
class EvidenceVerdict:
    status: str
    reason: str


def inspect_candidates(records: object, *, repository: str, commit_sha: str) -> EvidenceVerdict:
    """Detect invalid, conflicting or stale records; never grant trusted PASS."""
    if (
        not isinstance(repository, str)
        or _REPOSITORY.fullmatch(repository) is None
        or not isinstance(commit_sha, str)
        or _SHA.fullmatch(commit_sha) is None
        or not isinstance(records, tuple)
        or not 1 <= len(records) <= 1000
    ):
        return EvidenceVerdict("BLOCKED", "INVALID_BATCH")
    identities: set[tuple[str, str, int]] = set()
    for record in records:
        if not isinstance(record, EvidenceCandidate):
            return EvidenceVerdict("BLOCKED", "INVALID_RECORD")
        if any(
            not isinstance(value, str) or _ID.fullmatch(value) is None
            for value in (record.provider, record.run_id, record.source_ref)
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_IDENTITY")
        if (
            not isinstance(record.repository, str)
            or _REPOSITORY.fullmatch(record.repository) is None
            or not isinstance(record.commit_sha, str)
            or _SHA.fullmatch(record.commit_sha) is None
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_SOURCE_IDENTITY")
        if record.repository != repository or record.commit_sha != commit_sha:
            return EvidenceVerdict("BLOCKED", "SOURCE_DRIFT")
        if (
            isinstance(record.attempt, bool)
            or not isinstance(record.attempt, int)
            or record.attempt < 1
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_ATTEMPT")
        key = (record.provider, record.run_id, record.attempt)
        if key in identities:
            return EvidenceVerdict("BLOCKED", "DUPLICATE_ATTEMPT")
        identities.add(key)
        if not isinstance(record.conclusion, str) or record.conclusion not in (
            "success", "failure", "cancelled", "timed_out"
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_CONCLUSION")
        try:
            if (
                not isinstance(record.occurred_at, datetime)
                or record.occurred_at.tzinfo is None
                or record.occurred_at.utcoffset() is None
            ):
                return EvidenceVerdict("BLOCKED", "INVALID_TIMESTAMP")
            record.occurred_at.astimezone(timezone.utc)
        except Exception:
            # A custom tzinfo supplied by an untrusted record can raise arbitrarily.
            return EvidenceVerdict("BLOCKED", "INVALID_TIMESTAMP")
        if not isinstance(record.digest, str) or _DIGEST.fullmatch(record.digest) is None:
            return EvidenceVerdict("BLOCKED", "INVALID_DIGEST")
    return EvidenceVerdict("CANDIDATE_ONLY", "PROVIDER_AND_ANCHOR_UNVERIFIED")
