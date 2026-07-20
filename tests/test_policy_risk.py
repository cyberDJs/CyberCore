from cybercore.discovery import DiscoveryFinding
from cybercore.policy import PolicyEngine
from cybercore.risk import RiskEngine, risk_band


def _finding(identifier: str, detector: str, severity: str, subject: str) -> DiscoveryFinding:
    return DiscoveryFinding(
        id=identifier,
        detector=detector,
        severity=severity,
        subject_ref=subject,
        summary=f"{detector} finding",
        evidence=("registry",),
        proposed_action="Inspect and remediate.",
    )


def test_policy_engine_matches_discovery_contract() -> None:
    findings = (
        _finding("DISC-1", "backup-coverage", "high", "SERVICE-1"),
        _finding("DISC-2", "monitoring-coverage", "medium", "SERVICE-1"),
    )

    decisions = PolicyEngine().evaluate(findings)

    assert [decision.policy_id for decision in decisions] == [
        "POLICY-BACKUP-REQUIRED",
        "POLICY-MONITORING-REQUIRED",
    ]
    assert all(decision.subject_ref == "SERVICE-1" for decision in decisions)


def test_risk_engine_groups_subjects_and_caps_score() -> None:
    findings = (
        _finding("DISC-1", "backup-coverage", "high", "SERVICE-1"),
        _finding("DISC-2", "monitoring-coverage", "medium", "SERVICE-1"),
        _finding("DISC-3", "registry-unknown", "medium", "ASSET-1"),
    )
    decisions = PolicyEngine().evaluate(findings)

    assessments = RiskEngine().assess(findings, decisions)

    assert assessments[0].subject_ref == "SERVICE-1"
    assert assessments[0].score == 100
    assert assessments[0].band == "critical"
    assert assessments[1].subject_ref == "ASSET-1"
    assert assessments[1].score == 35
    assert assessments[1].band == "warning"


def test_risk_band_boundaries() -> None:
    assert risk_band(0) == "healthy"
    assert risk_band(20) == "warning"
    assert risk_band(40) == "high"
    assert risk_band(70) == "critical"
