from cybercore.discovery import DiscoveryFinding
from cybercore.planner import Planner
from cybercore.policy import PolicyDecision
from cybercore.risk import RiskAssessment


def test_planner_builds_deterministic_prioritized_action() -> None:
    finding = DiscoveryFinding(
        id="DISC-001",
        detector="backup-coverage",
        severity="high",
        subject_ref="ASSET-IVPS-001",
        summary="Backup coverage is unknown.",
        evidence=("registry:ASSET-IVPS-001.backup",),
        proposed_action="Verify backup scope.",
    )
    decision = PolicyDecision(
        policy_id="POLICY-BACKUP-REQUIRED",
        finding_id=finding.id,
        subject_ref=finding.subject_ref,
        risk_weight=35,
        recommendation="Define backup coverage and capture restore evidence.",
        rationale="matched",
    )
    assessment = RiskAssessment(
        subject_ref="ASSET-IVPS-001",
        score=70,
        band="critical",
        finding_ids=(finding.id,),
        policy_ids=(decision.policy_id,),
    )

    first = Planner().plan((finding,), (decision,), (assessment,))
    second = Planner().plan((finding,), (decision,), (assessment,))

    assert first == second
    assert len(first) == 1
    action = first[0]
    assert action.id.startswith("PLAN-")
    assert action.priority == 70
    assert action.risk == "critical"
    assert action.approval == "required"
    assert action.finding_ids == ("DISC-001",)
    assert action.policy_ids == ("POLICY-BACKUP-REQUIRED",)
    assert "restore evidence" in action.action


def test_planner_orders_highest_priority_first() -> None:
    assessments = (
        RiskAssessment("ASSET-B", 40, "high", (), ()),
        RiskAssessment("ASSET-A", 90, "critical", (), ()),
    )

    actions = Planner().plan((), (), assessments)

    assert [action.subject_ref for action in actions] == ["ASSET-A", "ASSET-B"]
