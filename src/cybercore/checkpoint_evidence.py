from __future__ import annotations

from pathlib import Path

from cybercore.checkpoint import RepositoryCheckpoint
from cybercore.verification_evidence import (
    VerificationEvidence,
    load_verification_evidence,
    validate_verification_evidence,
)


class CheckpointEvidenceError(ValueError):
    """Raised when checkpoint evidence options are invalid."""


def resolve_test_result(
    checkpoint: RepositoryCheckpoint,
    *,
    evidence_path: Path | None = None,
    test_result: str | None = None,
) -> tuple[str | None, VerificationEvidence | None]:
    if evidence_path is not None and test_result is not None:
        raise CheckpointEvidenceError(
            "--evidence cannot be combined with --test-result"
        )

    if evidence_path is None:
        return test_result, None

    evidence = load_verification_evidence(evidence_path)
    validate_verification_evidence(
        evidence,
        repository=Path(checkpoint.repository),
        commit=checkpoint.commit,
    )
    return evidence.summary, evidence
