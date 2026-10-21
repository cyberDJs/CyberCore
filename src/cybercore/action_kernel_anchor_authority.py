"""Policy checks for independently retained audit checkpoints.

This module does not create a trust anchor: the caller must authenticate the
external authority and durably retain the accepted checkpoint outside the
audit writer's security domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cybercore.action_kernel_audit_checkpoint import AuditCheckpoint


class TrustedAnchorStore(Protocol):
    """External authoritative interface implemented by a trusted application.

    Implementations MUST atomically enforce monotonic sequence transitions and
    retain the previous accepted checkpoint. A local same-authority file is not
    a valid production implementation.
    """

    def read_accepted(self, database_identity: str) -> AuditCheckpoint | None: ...

    def accept_if_current(
        self, previous: AuditCheckpoint | None, candidate: AuditCheckpoint
    ) -> bool: ...


@dataclass(frozen=True)
class AnchorDecision:
    accepted: bool
    reason: str


def check_anchor_transition(
    previous: AuditCheckpoint | None, candidate: AuditCheckpoint
) -> AnchorDecision:
    """Reject rollback, identity substitution, and same-height equivocation.

    This is only a pure preflight: an actual store MUST repeat the checks within
    an atomic compare-and-set transaction to prevent competing writers.
    """
    if previous is None:
        if candidate.sequence == 0:
            return AnchorDecision(False, "GENESIS_IS_NOT_EVIDENCE")
        return AnchorDecision(True, "INITIAL_CANDIDATE")
    if previous.database_identity != candidate.database_identity:
        return AnchorDecision(False, "DATABASE_IDENTITY_MISMATCH")
    if candidate.sequence < previous.sequence:
        return AnchorDecision(False, "ANCHOR_ROLLBACK")
    if candidate.sequence == previous.sequence:
        if candidate.event_hash != previous.event_hash:
            return AnchorDecision(False, "ANCHOR_EQUIVOCATION")
        return AnchorDecision(False, "ALREADY_ANCHORED")
    return AnchorDecision(True, "ADVANCED_CANDIDATE")


def verify_and_propose_anchor(
    path: str, *,
    candidate: AuditCheckpoint,
    previous: AuditCheckpoint | None,
) -> AnchorDecision:
    """Check local history against a candidate before external acceptance.

    The caller must get `previous` from a separate authenticated authority.
    There is deliberately no automatic publish/write action.
    """
    from cybercore.action_kernel_audit_checkpoint import verify_anchored_checkpoint

    decision = check_anchor_transition(previous, candidate)
    if not decision.accepted:
        return decision
    if not verify_anchored_checkpoint(
        path,
        trusted_checkpoint=candidate,
        expected_database_identity=candidate.database_identity,
    ):
        return AnchorDecision(False, "LOCAL_HISTORY_MISMATCH")
    return decision
