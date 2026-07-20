from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cybercore.discovery import DiscoveryFinding


@dataclass(frozen=True, slots=True)
class PolicyRule:
    id: str
    detectors: tuple[str, ...]
    severities: tuple[str, ...]
    risk_weight: int
    recommendation: str

    def matches(self, finding: DiscoveryFinding) -> bool:
        return finding.detector in self.detectors and finding.severity in self.severities


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    policy_id: str
    finding_id: str
    subject_ref: str | None
    risk_weight: int
    recommendation: str
    rationale: str


DEFAULT_POLICIES: tuple[PolicyRule, ...] = (
    PolicyRule(
        id="POLICY-BACKUP-REQUIRED",
        detectors=("backup",),
        severities=("warning", "high", "critical"),
        risk_weight=35,
        recommendation="Define backup coverage and capture restore evidence.",
    ),
    PolicyRule(
        id="POLICY-MONITORING-REQUIRED",
        detectors=("monitoring",),
        severities=("warning", "high", "critical"),
        risk_weight=25,
        recommendation="Configure monitoring and an alert destination.",
    ),
    PolicyRule(
        id="POLICY-DEGRADED-SERVICE",
        detectors=("service-health",),
        severities=("high", "critical"),
        risk_weight=40,
        recommendation="Investigate and restore the degraded service.",
    ),
    PolicyRule(
        id="POLICY-INVENTORY-COMPLETENESS",
        detectors=("unknown", "endpoint"),
        severities=("warning", "high", "critical"),
        risk_weight=15,
        recommendation="Collect evidence and complete the registry record.",
    ),
)


class PolicyEngine:
    def __init__(self, rules: Iterable[PolicyRule] = DEFAULT_POLICIES) -> None:
        self.rules = tuple(rules)

    def evaluate(self, findings: Iterable[DiscoveryFinding]) -> tuple[PolicyDecision, ...]:
        decisions: list[PolicyDecision] = []
        for finding in findings:
            for rule in self.rules:
                if not rule.matches(finding):
                    continue
                decisions.append(
                    PolicyDecision(
                        policy_id=rule.id,
                        finding_id=finding.id,
                        subject_ref=finding.subject_ref,
                        risk_weight=rule.risk_weight,
                        recommendation=rule.recommendation,
                        rationale=f"{rule.id} matched {finding.detector}/{finding.severity}",
                    )
                )
        return tuple(decisions)
