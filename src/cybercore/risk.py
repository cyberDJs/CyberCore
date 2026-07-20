from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cybercore.discovery import DiscoveryFinding
from cybercore.policy import PolicyDecision


SEVERITY_POINTS = {
    "info": 5,
    "warning": 20,
    "high": 35,
    "critical": 50,
}


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    subject_ref: str
    score: int
    band: str
    finding_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]


def risk_band(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 40:
        return "high"
    if score >= 20:
        return "warning"
    return "healthy"


class RiskEngine:
    def assess(
        self,
        findings: Iterable[DiscoveryFinding],
        decisions: Iterable[PolicyDecision],
    ) -> tuple[RiskAssessment, ...]:
        finding_values = tuple(findings)
        decision_values = tuple(decisions)
        subjects = sorted({finding.subject_ref for finding in finding_values if finding.subject_ref})
        assessments: list[RiskAssessment] = []

        for subject in subjects:
            subject_findings = tuple(item for item in finding_values if item.subject_ref == subject)
            subject_decisions = tuple(item for item in decision_values if item.subject_ref == subject)
            severity_score = sum(SEVERITY_POINTS.get(item.severity, 0) for item in subject_findings)
            policy_score = sum(item.risk_weight for item in subject_decisions)
            score = min(100, severity_score + policy_score)
            assessments.append(
                RiskAssessment(
                    subject_ref=subject,
                    score=score,
                    band=risk_band(score),
                    finding_ids=tuple(sorted(item.id for item in subject_findings)),
                    policy_ids=tuple(sorted({item.policy_id for item in subject_decisions})),
                )
            )

        return tuple(sorted(assessments, key=lambda item: (-item.score, item.subject_ref)))
