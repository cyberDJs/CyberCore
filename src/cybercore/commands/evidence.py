from __future__ import annotations

from pathlib import Path
from typing import Sequence

from cybercore.repository_identity_policy import (
    enforce_configured_repository_identity_policy,
)
from cybercore.verification_evidence import VerificationEvidence
from cybercore.verification_runner import run_verification


def run_evidence_command(
    repo: Path,
    command: Sequence[str],
    *,
    summary: str,
    output: Path,
) -> VerificationEvidence:
    """Run a verification command and persist commit-bound evidence."""
    enforce_configured_repository_identity_policy(
        repo,
        operation="Verification evidence generation",
    )
    normalized = list(command)
    if normalized and normalized[0] == "--":
        normalized = normalized[1:]
    return run_verification(
        repo,
        normalized,
        summary=summary,
        output=output,
    )
