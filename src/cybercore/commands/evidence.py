from __future__ import annotations

from pathlib import Path
from typing import Sequence

from cybercore.trusted_operation_context import enforce_trusted_operation_context
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
    enforce_trusted_operation_context(
        repo,
        operation="verification_evidence",
        risk="medium",
        require_clean=True,
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
