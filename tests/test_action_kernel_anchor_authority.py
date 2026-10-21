from pathlib import Path

from cybercore.action_kernel_anchor_authority import check_anchor_transition, verify_and_propose_anchor
from cybercore.action_kernel_audit_checkpoint import AuditCheckpoint


def _anchor(seq: int, digest: str = "a", identity: str = "auditor-A") -> AuditCheckpoint:
    return AuditCheckpoint(seq, digest * 64, identity)


def test_rejects_genesis_as_initial_evidence() -> None:
    decision = check_anchor_transition(None, _anchor(0, "0"))
    assert decision.reason == "GENESIS_IS_NOT_EVIDENCE"
    assert not decision.accepted


def test_allows_first_nonempty_checkpoint() -> None:
    assert check_anchor_transition(None, _anchor(1)).accepted


def test_rejects_rollback_and_identity_switch() -> None:
    previous = _anchor(5)
    assert check_anchor_transition(previous, _anchor(4)).reason == "ANCHOR_ROLLBACK"
    assert check_anchor_transition(previous, _anchor(6, identity="auditor-B")).reason == "DATABASE_IDENTITY_MISMATCH"


def test_rejects_equivocation_and_duplicate() -> None:
    previous = _anchor(5)
    assert check_anchor_transition(previous, _anchor(5, "b")).reason == "ANCHOR_EQUIVOCATION"
    assert check_anchor_transition(previous, previous).reason == "ALREADY_ANCHORED"


def test_allows_monotonic_advance() -> None:
    assert check_anchor_transition(_anchor(5), _anchor(6, "b")).accepted


def test_missing_audit_db_cannot_propose_anchor(tmp_path: Path) -> None:
    candidate = _anchor(1)
    result = verify_and_propose_anchor(
        str(tmp_path / "missing.sqlite"), candidate=candidate, previous=None
    )
    assert not result.accepted
    assert result.reason == "LOCAL_HISTORY_MISMATCH"
