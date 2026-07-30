from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from cybercore.checkpoint import RepositoryCheckpoint
from cybercore.operation_context_disclosure import (
    sanitize_disclosure_text,
    sanitize_legacy_command_string,
)


class VerificationEvidenceError(ValueError):
    """Raised when verification evidence is missing, malformed, or untrusted."""


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    command: str
    exit_code: int
    duration: float
    summary: str
    repository_binding: str
    commit: str
    generated_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VerificationEvidence":
        required = {
            "command",
            "exit_code",
            "duration",
            "summary",
            "commit",
            "generated_at",
        }
        has_binding = "repository_binding" in payload
        has_legacy_repository = "repository" in payload
        if not has_binding and not has_legacy_repository:
            required.add("repository_binding")
        missing = sorted(required - payload.keys())
        if missing:
            raise VerificationEvidenceError(
                "Verification evidence missing fields: " + ", ".join(missing)
            )

        try:
            repository_binding = (
                str(payload["repository_binding"]).strip()
                if has_binding
                else repository_evidence_binding(Path(str(payload["repository"]).strip()))
            )
            evidence = cls(
                command=sanitize_legacy_command_string(str(payload["command"]).strip()),
                exit_code=int(payload["exit_code"]),
                duration=float(payload["duration"]),
                summary=sanitize_disclosure_text(str(payload["summary"]).strip()),
                repository_binding=repository_binding,
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
            raise VerificationEvidenceError("Verification evidence duration must be non-negative")
        if not evidence.summary:
            raise VerificationEvidenceError("Verification evidence summary is empty")
        if not evidence.repository_binding:
            raise VerificationEvidenceError("Verification evidence repository binding is empty")
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
            raise VerificationEvidenceError(f"Invalid verification evidence JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise VerificationEvidenceError("Verification evidence root must be an object")
        return cls.from_dict(payload)

    def validate_for(self, checkpoint: RepositoryCheckpoint) -> None:
        validate_verification_evidence(
            self,
            repository=Path(checkpoint.repository),
            commit=checkpoint.commit,
        )

    def checkpoint_summary(self) -> str:
        return f"{self.summary} via `{self.command}` in {self.duration:.2f}s"


def load_verification_evidence(path: Path) -> VerificationEvidence:
    """Load and validate the structure of a verification evidence JSON file."""
    return VerificationEvidence.from_file(path)


def repository_evidence_binding(repository: Path) -> str:
    """Return a non-reversible binding for local repository evidence."""
    resolved = str(repository.expanduser().resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def validate_verification_evidence(
    evidence: VerificationEvidence,
    *,
    repository: Path,
    commit: str,
) -> None:
    """Validate successful evidence against one repository and exact commit."""
    if evidence.exit_code != 0:
        raise VerificationEvidenceError(
            f"Verification command failed with exit code {evidence.exit_code}"
        )

    expected_binding = repository_evidence_binding(repository)
    if evidence.repository_binding != expected_binding:
        raise VerificationEvidenceError(
            "Verification evidence repository does not match checkpoint repository"
        )

    if evidence.commit != commit:
        raise VerificationEvidenceError(
            "Verification evidence commit does not match checkpoint commit"
        )
