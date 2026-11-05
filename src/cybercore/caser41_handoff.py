"""Fail-closed, pure CASER handoff sanity checks for interrupted runs.

Handoff data is untrusted evidence, not authority to resume a write.
The caller must re-read canonical provider state and separately authorize actions.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
_SAFE_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}", re.ASCII)

TRANSACTION_STATES = frozenset(
    {
        "PLANNED",
        "ACTIVE",
        "VERIFYING",
        "COMMITTED",
        "COMPENSATING",
        "ROLLED_BACK",
        "PARTIAL",
        "BLOCKED",
        "FAILED",
    }
)


@dataclass(frozen=True)
class HandoffSnapshot:
    run_id: str
    repository: str
    source_sha: str
    transaction_state: str
    completed_actions: tuple[str, ...]
    pending_action: str | None
    open_side_effects: tuple[str, ...]
    last_verified_step: str | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class HandoffVerdict:
    status: str
    reason: str


def assess_handoff(
    snapshot: HandoffSnapshot,
    *,
    expected_run_id: str,
    canonical_repository: str,
    current_sha: str,
) -> HandoffVerdict:
    """Permit read-only reconciliation only; never authorize mutable replay."""
    if not isinstance(snapshot, HandoffSnapshot):
        return HandoffVerdict("BLOCKED", "INVALID_HANDOFF_SHAPE")
    if any(
        not isinstance(value, str)
        for value in (
            snapshot.run_id,
            snapshot.repository,
            snapshot.source_sha,
            snapshot.transaction_state,
            expected_run_id,
            canonical_repository,
            current_sha,
        )
    ):
        return HandoffVerdict("BLOCKED", "INVALID_HANDOFF_SHAPE")
    if any(
        value is not None and not isinstance(value, str)
        for value in (snapshot.pending_action, snapshot.last_verified_step)
    ):
        return HandoffVerdict("BLOCKED", "INVALID_HANDOFF_SHAPE")
    if any(
        not isinstance(items, tuple) or any(not isinstance(item, str) for item in items)
        for items in (
            snapshot.completed_actions,
            snapshot.open_side_effects,
            snapshot.evidence_refs,
        )
    ):
        return HandoffVerdict("BLOCKED", "INVALID_HANDOFF_SHAPE")
    if not _SAFE_ID.fullmatch(snapshot.run_id) or snapshot.run_id != expected_run_id:
        return HandoffVerdict("BLOCKED", "RUN_ID_MISMATCH")
    if (
        snapshot.repository != canonical_repository
        or not snapshot.repository.strip()
        or any(char.isspace() for char in snapshot.repository)
    ):
        return HandoffVerdict("BLOCKED", "REPOSITORY_MISMATCH")
    if snapshot.transaction_state not in TRANSACTION_STATES:
        return HandoffVerdict("BLOCKED", "INVALID_TRANSACTION_STATE")
    if _SHA.fullmatch(snapshot.source_sha) is None or _SHA.fullmatch(current_sha) is None:
        return HandoffVerdict("BLOCKED", "INVALID_COMMIT_ID")
    if len(snapshot.completed_actions) != len(set(snapshot.completed_actions)):
        return HandoffVerdict("BLOCKED", "DUPLICATE_ACTION_RECEIPT")
    if any(not _SAFE_ID.fullmatch(action) for action in snapshot.completed_actions):
        return HandoffVerdict("BLOCKED", "INVALID_ACTION_ID")
    if snapshot.pending_action is not None and not _SAFE_ID.fullmatch(snapshot.pending_action):
        return HandoffVerdict("BLOCKED", "INVALID_PENDING_ACTION")
    if snapshot.pending_action in snapshot.completed_actions:
        return HandoffVerdict("BLOCKED", "PENDING_ALREADY_COMPLETED")
    if any(not _SAFE_ID.fullmatch(item) for item in snapshot.open_side_effects):
        return HandoffVerdict("BLOCKED", "INVALID_SIDE_EFFECT_ID")
    if snapshot.last_verified_step is not None and not _SAFE_ID.fullmatch(
        snapshot.last_verified_step
    ):
        return HandoffVerdict("BLOCKED", "INVALID_VERIFIED_STEP")
    if any(not ref.strip() for ref in snapshot.evidence_refs):
        return HandoffVerdict("BLOCKED", "INVALID_EVIDENCE_REF")
    if snapshot.open_side_effects or snapshot.transaction_state in {
        "ACTIVE",
        "VERIFYING",
        "COMPENSATING",
        "PARTIAL",
    }:
        return HandoffVerdict("BLOCKED", "MUTATION_OUTCOME_REQUIRES_RECONCILIATION")
    if snapshot.transaction_state in {"FAILED", "BLOCKED"}:
        return HandoffVerdict("BLOCKED", "PRIOR_RUN_TERMINAL_FAILURE")
    if snapshot.transaction_state in {"COMMITTED", "ROLLED_BACK"}:
        return HandoffVerdict("READONLY_RECONCILE", "TERMINAL_RUN_VERIFY_EFFECT")
    if snapshot.completed_actions:
        return HandoffVerdict("BLOCKED", "COMPLETED_ACTIONS_REQUIRE_RECONCILIATION")
    if snapshot.source_sha != current_sha:
        return HandoffVerdict("REPLAN_REQUIRED", "CANONICAL_SOURCE_DRIFT")
    return HandoffVerdict("READONLY_RECONCILE", "PLAN_REQUIRES_FRESH_PREFLIGHT")
