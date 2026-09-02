from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json


_ALLOWED_VERDICTS = {"PASS", "FAIL"}


def evidence_digest(evidence: dict[str, object]) -> str:
    encoded = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    evaluator_id: str
    evaluator_version: str
    score: float
    verdict: str
    reasons: tuple[str, ...]
    evidence_digest: str

    def validate(self, *, expected_evidence_digest: str) -> None:
        if not self.evaluator_id.strip() or not self.evaluator_version.strip():
            raise ValueError("evaluator identity and version are required")
        if isinstance(self.score, bool) or not 0.0 <= self.score <= 1.0:
            raise ValueError("evaluation score must be between 0 and 1")
        if self.verdict not in _ALLOWED_VERDICTS:
            raise ValueError("evaluation verdict must be PASS or FAIL")
        if not self.reasons or not all(reason.strip() for reason in self.reasons):
            raise ValueError("evaluation reasons must contain non-empty strings")
        if self.evidence_digest != expected_evidence_digest:
            raise ValueError("evaluation evidence digest does not match executor evidence")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "score": self.score,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "evidence_digest": self.evidence_digest,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def event_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["evaluation_digest"] = self.digest
        return payload
