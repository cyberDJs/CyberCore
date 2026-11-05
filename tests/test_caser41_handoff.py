from dataclasses import replace

from cybercore.caser41_handoff import HandoffSnapshot, assess_handoff

SHA = "a" * 40


def _snapshot() -> HandoffSnapshot:
    return HandoffSnapshot(
        run_id="caser-run-001",
        repository="cyberDJs/CyberCore",
        source_sha=SHA,
        transaction_state="PLANNED",
        completed_actions=(),
        pending_action="inspect",
        open_side_effects=(),
        last_verified_step=None,
        evidence_refs=(),
    )


def _verdict(snapshot: HandoffSnapshot, *, sha: str = SHA) -> str:
    return assess_handoff(
        snapshot,
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha=sha,
    ).reason


def test_clean_plan_is_readonly_only() -> None:
    decision = assess_handoff(
        _snapshot(),
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha=SHA,
    )
    assert decision.status == "READONLY_RECONCILE"
    assert decision.reason == "PLAN_REQUIRES_FRESH_PREFLIGHT"


def test_drift_requires_replan() -> None:
    decision = assess_handoff(
        _snapshot(),
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha="b" * 40,
    )
    assert decision.status == "REPLAN_REQUIRED"


def test_forged_run_or_repo_is_blocked() -> None:
    assert _verdict(replace(_snapshot(), run_id="other")) == "RUN_ID_MISMATCH"
    assert _verdict(replace(_snapshot(), repository="other/repo")) == "REPOSITORY_MISMATCH"


def test_unresolved_write_never_replays_automatically() -> None:
    snapshot = replace(_snapshot(), transaction_state="ACTIVE", open_side_effects=("deploy",))
    assert _verdict(snapshot) == "MUTATION_OUTCOME_REQUIRES_RECONCILIATION"


def test_active_transaction_without_recorded_effect_still_blocks() -> None:
    assert (
        _verdict(replace(_snapshot(), transaction_state="ACTIVE"))
        == "MUTATION_OUTCOME_REQUIRES_RECONCILIATION"
    )


def test_duplicate_and_conflicting_action_receipts_block() -> None:
    duplicate = replace(_snapshot(), completed_actions=("write", "write"))
    assert _verdict(duplicate) == "DUPLICATE_ACTION_RECEIPT"
    conflicting = replace(_snapshot(), completed_actions=("write",), pending_action="write")
    assert _verdict(conflicting) == "PENDING_ALREADY_COMPLETED"


def test_invalid_sha_or_state_is_blocked() -> None:
    assert _verdict(replace(_snapshot(), source_sha="HEAD")) == "INVALID_COMMIT_ID"
    assert _verdict(replace(_snapshot(), transaction_state="DONE")) == "INVALID_TRANSACTION_STATE"


def test_failed_state_and_committed_state_are_not_resume_grants() -> None:
    assert (
        _verdict(replace(_snapshot(), transaction_state="FAILED")) == "PRIOR_RUN_TERMINAL_FAILURE"
    )
    decision = assess_handoff(
        replace(_snapshot(), transaction_state="COMMITTED", pending_action=None),
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha=SHA,
    )
    assert decision.status == "READONLY_RECONCILE"
    assert decision.reason == "TERMINAL_RUN_VERIFY_EFFECT"


def test_drift_and_open_mutation_prioritizes_block_over_replan() -> None:
    snapshot = replace(_snapshot(), transaction_state="ACTIVE", open_side_effects=("deploy",))
    decision = assess_handoff(
        snapshot,
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha="b" * 40,
    )
    assert decision.status == "BLOCKED"
    assert decision.reason == "MUTATION_OUTCOME_REQUIRES_RECONCILIATION"


def test_stale_snapshot_with_open_side_effect_also_blocks() -> None:
    snapshot = replace(_snapshot(), open_side_effects=("write",))
    decision = assess_handoff(
        snapshot,
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha="b" * 40,
    )
    assert decision.status == "BLOCKED"


def test_terminal_committed_drift_requires_effect_verification() -> None:
    snapshot = replace(_snapshot(), transaction_state="COMMITTED", pending_action=None)
    decision = assess_handoff(
        snapshot,
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha="b" * 40,
    )
    assert decision.status == "READONLY_RECONCILE"
    assert decision.reason == "TERMINAL_RUN_VERIFY_EFFECT"


def test_terminal_rollback_drift_requires_effect_verification() -> None:
    snapshot = replace(_snapshot(), transaction_state="ROLLED_BACK", pending_action=None)
    assert _verdict(snapshot, sha="b" * 40) == "TERMINAL_RUN_VERIFY_EFFECT"


def test_failed_or_blocked_drift_remains_blocked() -> None:
    for state in ("FAILED", "BLOCKED"):
        snapshot = replace(_snapshot(), transaction_state=state, pending_action=None)
        decision = assess_handoff(
            snapshot,
            expected_run_id="caser-run-001",
            canonical_repository="cyberDJs/CyberCore",
            current_sha="b" * 40,
        )
        assert decision.status == "BLOCKED"
        assert decision.reason == "PRIOR_RUN_TERMINAL_FAILURE"


def test_clean_plan_with_drift_can_require_replan() -> None:
    assert _verdict(_snapshot(), sha="b" * 40) == "CANONICAL_SOURCE_DRIFT"


def test_completed_receipt_in_planned_state_blocks_replan() -> None:
    snapshot = replace(_snapshot(), completed_actions=("deploy",), pending_action="inspect")
    decision = assess_handoff(
        snapshot,
        expected_run_id="caser-run-001",
        canonical_repository="cyberDJs/CyberCore",
        current_sha="b" * 40,
    )
    assert decision.status == "BLOCKED"
    assert decision.reason == "COMPLETED_ACTIONS_REQUIRE_RECONCILIATION"


def test_completed_receipt_in_planned_state_blocks_even_without_drift() -> None:
    snapshot = replace(_snapshot(), completed_actions=("deploy",))
    assert _verdict(snapshot) == "COMPLETED_ACTIONS_REQUIRE_RECONCILIATION"


def test_committed_completed_receipt_still_requires_effect_verification() -> None:
    snapshot = replace(
        _snapshot(),
        completed_actions=("deploy",),
        pending_action=None,
        transaction_state="COMMITTED",
    )
    assert _verdict(snapshot, sha="b" * 40) == "TERMINAL_RUN_VERIFY_EFFECT"
