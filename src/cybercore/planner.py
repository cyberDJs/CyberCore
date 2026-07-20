from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable

from cybercore.discovery import DiscoveryFinding
from cybercore.policy import PolicyDecision
from cybercore.risk import RiskAssessment


@dataclass(frozen=True, slots=True)
class PlannedAction:
    id: str
    subject_ref: str
    priority: int
    risk: str
    action: str
    approval: str
    finding_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]
    rationale: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("finding_ids", "policy_ids", "rationale"):
            payload[key] = list(payload[key])
        return payload


def _plan_id(subject_ref: str, finding_ids: Iterable[str], policy_ids: Iterable[str]) -> str:
    source = "|".join((subject_ref, *sorted(finding_ids), *sorted(policy_ids))).encode("utf-8")
    return f"PLAN-{hashlib.sha256(source).hexdigest()[:12].upper()}"


def _approval_for(risk: str) -> str:
    return "required" if risk in {"high", "critical"} else "review"


class Planner:
    """Builds deterministic, explainable actions from discovery, policy, and risk."""

    def plan(
        self,
        findings: Iterable[DiscoveryFinding],
        decisions: Iterable[PolicyDecision],
        assessments: Iterable[RiskAssessment],
    ) -> tuple[PlannedAction, ...]:
        finding_values = tuple(findings)
        decision_values = tuple(decisions)
        actions: list[PlannedAction] = []

        for assessment in assessments:
            subject_findings = tuple(item for item in finding_values if item.subject_ref == assessment.subject_ref)
            subject_decisions = tuple(item for item in decision_values if item.subject_ref == assessment.subject_ref)
            recommendations = tuple(dict.fromkeys(item.recommendation for item in subject_decisions))
            fallback_actions = tuple(dict.fromkeys(item.proposed_action for item in subject_findings))
            action = " ".join(recommendations or fallback_actions) or "Collect evidence and define remediation."
            rationale = tuple(
                [f"risk={assessment.band}:{assessment.score}"]
                + [f"finding={item.id}:{item.detector}/{item.severity}" for item in subject_findings]
                + [f"policy={item.policy_id}" for item in subject_decisions]
            )
            actions.append(
                PlannedAction(
                    id=_plan_id(assessment.subject_ref, assessment.finding_ids, assessment.policy_ids),
                    subject_ref=assessment.subject_ref,
                    priority=assessment.score,
                    risk=assessment.band,
                    action=action,
                    approval=_approval_for(assessment.band),
                    finding_ids=assessment.finding_ids,
                    policy_ids=assessment.policy_ids,
                    rationale=rationale,
                )
            )

        return tuple(sorted(actions, key=lambda item: (-item.priority, item.subject_ref, item.id)))
