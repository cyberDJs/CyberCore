from cybercore.integrations.howedo import ContinuityDecision, normalize_howedo_decision
from cybercore.integrations.oathdo import GovernanceDecision, normalize_oathdo_decision


def test_unknown_howedo_decision_fails_closed() -> None:
    result = normalize_howedo_decision("whatever")
    assert result.decision is ContinuityDecision.ABORT
    assert result.allows_standard_progress is False


def test_known_howedo_decision_is_preserved() -> None:
    result = normalize_howedo_decision("continue", witness_id="w1")
    assert result.decision is ContinuityDecision.CONTINUE
    assert result.witness_id == "w1"
    assert result.allows_standard_progress is True


def test_unknown_oathdo_decision_fails_closed() -> None:
    result = normalize_oathdo_decision("whatever")
    assert result.decision is GovernanceDecision.DENY


def test_known_oathdo_decision_is_preserved() -> None:
    result = normalize_oathdo_decision("approval_required", evidence_id="e1")
    assert result.decision is GovernanceDecision.APPROVAL_REQUIRED
    assert result.evidence_id == "e1"
