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
_REPOSITORY = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", re.ASCII
)


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
        type(repository) is not str
        or _REPOSITORY.fullmatch(repository) is None
        or type(commit_sha) is not str
        or _SHA.fullmatch(commit_sha) is None
        or type(records) is not tuple
        or not 1 <= len(records) <= 1000
    ):
        return EvidenceVerdict("BLOCKED", "INVALID_BATCH")
    identities: set[tuple[str, str, int]] = set()
    for record in records:
        if type(record) is not EvidenceCandidate:
            return EvidenceVerdict("BLOCKED", "INVALID_RECORD")
        try:
            (
                provider,
                run_id,
                attempt,
                source_repository,
                source_commit,
                conclusion,
                occurred_at,
                digest,
                source_ref,
            ) = (
                record.provider,
                record.run_id,
                record.attempt,
                record.repository,
                record.commit_sha,
                record.conclusion,
                record.occurred_at,
                record.digest,
                record.source_ref,
            )
        except AttributeError:
            return EvidenceVerdict("BLOCKED", "INVALID_RECORD")
        if any(
            type(value) is not str or _ID.fullmatch(value) is None
            for value in (provider, run_id, source_ref)
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_IDENTITY")
        if (
            type(source_repository) is not str
            or _REPOSITORY.fullmatch(source_repository) is None
            or type(source_commit) is not str
            or _SHA.fullmatch(source_commit) is None
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_SOURCE_IDENTITY")
        if source_repository != repository or source_commit != commit_sha:
            return EvidenceVerdict("BLOCKED", "SOURCE_DRIFT")
        if type(attempt) is not int or attempt < 1:
            return EvidenceVerdict("BLOCKED", "INVALID_ATTEMPT")
        key = (provider, run_id, attempt)
        if key in identities:
            return EvidenceVerdict("BLOCKED", "DUPLICATE_ATTEMPT")
        identities.add(key)
        if type(conclusion) is not str or conclusion not in (
            "success",
            "failure",
            "cancelled",
            "timed_out",
        ):
            return EvidenceVerdict("BLOCKED", "INVALID_CONCLUSION")
        try:
            if (
                type(occurred_at) is not datetime
                or occurred_at.tzinfo is None
                or occurred_at.utcoffset() is None
            ):
                return EvidenceVerdict("BLOCKED", "INVALID_TIMESTAMP")
            occurred_at.astimezone(timezone.utc)
        except Exception:
            # A custom tzinfo supplied by an untrusted record can raise arbitrarily.
            return EvidenceVerdict("BLOCKED", "INVALID_TIMESTAMP")
        if type(digest) is not str or _DIGEST.fullmatch(digest) is None:
            return EvidenceVerdict("BLOCKED", "INVALID_DIGEST")
    return EvidenceVerdict("CANDIDATE_ONLY", "PROVIDER_AND_ANCHOR_UNVERIFIED")
