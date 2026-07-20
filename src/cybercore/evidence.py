from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Iterable

from cybercore.discovery import DiscoveryFinding
from cybercore.registry import Registry


CONFIDENCE_VALUES = {
    "high": 0.9,
    "medium": 0.65,
    "low": 0.35,
}


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    finding_id: str
    subject_ref: str | None
    confidence: float
    freshness: str
    provenance: tuple[str, ...]
    verified: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["provenance"] = list(self.provenance)
        payload["reasons"] = list(self.reasons)
        return payload


def _freshness(last_reviewed: object, today: date) -> tuple[str, str]:
    if not isinstance(last_reviewed, str):
        return "unknown", "registry record has no valid last_reviewed date"
    try:
        reviewed = date.fromisoformat(last_reviewed[:10])
    except ValueError:
        return "unknown", "registry record has an invalid last_reviewed date"
    age = (today - reviewed).days
    if age < 0:
        return "unknown", "registry review date is in the future"
    if age <= 30:
        return "fresh", f"registry reviewed {age} days ago"
    if age <= 90:
        return "aging", f"registry reviewed {age} days ago"
    return "stale", f"registry reviewed {age} days ago"


def _confidence(evidence: object) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if not isinstance(evidence, list) or not evidence:
        return 0.0, (), ("registry record has no structured evidence",)

    values: list[float] = []
    provenance: list[str] = []
    reasons: list[str] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        confidence = CONFIDENCE_VALUES.get(str(item.get("confidence", "")).lower(), 0.25)
        values.append(confidence)
        source_type = str(item.get("type", "unknown"))
        reference = str(item.get("reference", "unspecified"))
        provenance.append(f"{source_type}:{reference}")

    if not values:
        return 0.0, tuple(provenance), ("structured evidence contains no usable entries",)

    score = min(1.0, max(values) + max(0, len(values) - 1) * 0.05)
    reasons.append(f"{len(values)} evidence source(s), strongest confidence={max(values):.2f}")
    return round(score, 2), tuple(dict.fromkeys(provenance)), tuple(reasons)


class EvidenceEngine:
    """Evaluates whether discovery findings are supported by current registry evidence."""

    def __init__(self, registry: Registry, today: date | None = None) -> None:
        self.registry = registry
        self.today = today or date.today()

    def assess(self, findings: Iterable[DiscoveryFinding]) -> tuple[EvidenceAssessment, ...]:
        assessments: list[EvidenceAssessment] = []
        for finding in findings:
            record = self.registry.get(finding.subject_ref) if finding.subject_ref else None
            if record is None:
                provenance = tuple(finding.evidence)
                assessments.append(
                    EvidenceAssessment(
                        finding_id=finding.id,
                        subject_ref=finding.subject_ref,
                        confidence=0.35 if provenance else 0.0,
                        freshness="unknown",
                        provenance=provenance,
                        verified=False,
                        reasons=("subject is not a registry entity; direct verification is required",),
                    )
                )
                continue

            confidence, provenance, confidence_reasons = _confidence(record.data.get("evidence"))
            freshness, freshness_reason = _freshness(record.data.get("last_reviewed"), self.today)
            verified = confidence >= 0.75 and freshness == "fresh" and bool(provenance)
            reasons = confidence_reasons + (freshness_reason,)
            if not verified:
                reasons += ("evidence does not meet the verification threshold",)
            assessments.append(
                EvidenceAssessment(
                    finding_id=finding.id,
                    subject_ref=finding.subject_ref,
                    confidence=confidence,
                    freshness=freshness,
                    provenance=provenance,
                    verified=verified,
                    reasons=reasons,
                )
            )

        return tuple(sorted(assessments, key=lambda item: (item.finding_id, item.subject_ref or "")))
