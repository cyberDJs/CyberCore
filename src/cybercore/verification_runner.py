from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from time import monotonic
from typing import Sequence

from cybercore.checkpoint import collect_checkpoint
from cybercore.verification_evidence import VerificationEvidence


class VerificationRunError(ValueError):
    """Raised when a verification command cannot be executed safely."""


def run_verification(
    repo: Path,
    command: Sequence[str],
    *,
    summary: str,
    output: Path,
) -> VerificationEvidence:
    repo = repo.expanduser().resolve()
    if not command:
        raise VerificationRunError("Verification command is empty")
    if not summary.strip():
        raise VerificationRunError("Verification summary is empty")

    checkpoint = collect_checkpoint(repo)
    started = monotonic()
    completed = subprocess.run(
        list(command),
        cwd=repo,
        check=False,
    )
    duration = monotonic() - started

    evidence = VerificationEvidence(
        command=" ".join(command),
        exit_code=completed.returncode,
        duration=duration,
        summary=summary.strip(),
        repository=checkpoint.repository,
        commit=checkpoint.commit,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )

    output = output.expanduser()
    if not output.is_absolute():
        output = repo / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(evidence), indent=2) + "\n", encoding="utf-8")
    return evidence
