from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from cybercore.checkpoint import RepositoryCheckpoint


class VerificationEvidenceError(ValueError):
    """Raised when verification evidence is missing, malformed, or untrusted."""


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    command: str
    exit_code: int
    duration: float
    summary: str
    repository: str
    commit: str
    generated_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VerificationEvidence":
        required = {
            "command",
            "exit_code",
            "duration",
            "summary",
            "repository",
            "commit",
            "generated_at",
        }
        missing = sorted(required - payload.keys())
        if missing:
            raise VerificationEvidenceError(
                "Verification evidence missing fields: " + ", ".join(missing)
            )

        try:
            evidence = cls(
                command=str(payload["command"]).strip(),
                exit_code=int(payload["exit_code"]),
                duration=float(payload["duration"]),
                summary=str(payload["summary"]).strip(),
                repository=str(payload["repository"]).strip(),
                commit=str(payload["commit"]).strip(),
                generated_at=str(payload["generated_at"]).strip(),
            )
        except (TypeError, ValueError) as exc:
            raise VerificationEvidenceError(
                f"Invalid verification evidence field type: {exc}"
            ) from exc

        if not evidence.command:
            raise VerificationEvidenceError("Verification evidence command is empty")
        if evidence.duration < 0:
            raise VerificationEvidenceError(
                "Verification evidence duration must be non-negative"
            )
        if not evidence.summary:
            raise VerificationEvidenceError("Verification evidence summary is empty")
        if not evidence.repository:
            raise VerificationEvidenceError("Verification evidence repository is empty")
        if not evidence.commit:
            raise VerificationEvidenceError("Verification evidence commit is empty")
        if not evidence.generated_at:
            raise VerificationEvidenceError("Verification evidence generated_at is empty")
        return evidence

    @classmethod
    def from_file(cls, path: Path) -> "VerificationEvidence":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise VerificationEvidenceError(f"Verification evidence not found: {path}")
        except json.JSONDecodeError as exc:
            raise VerificationEvidenceError(
                f"Invalid verification evidence JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise VerificationEvidenceError("Verification evidence root must be an object")
        return cls.from_dict(payload)

    def validate_for(self, checkpoint: RepositoryCheckpoint) -> None:
        if self.exit_code != 0:
            raise VerificationEvidenceError(
                f"Verification command failed with exit code {self.exit_code}"
            )
        evidence_repo = str(Path(self.repository).expanduser().resolve())
        if evidence_repo != checkpoint.repository:
            raise VerificationEvidenceError(
                "Verification evidence repository does not match checkpoint repository"
            )
        if self.commit != checkpoint.commit:
            raise VerificationEvidenceError(
                "Verification evidence commit does not match checkpoint commit"
            )

    def checkpoint_summary(self) -> str:
        return f"{self.summary} via `{self.command}` in {self.duration:.2f}s"


def load_verification_evidence(path: Path) -> VerificationEvidence:
    """Load and validate the structure of a verification evidence JSON file."""
    return VerificationEvidence.from_file(path)
