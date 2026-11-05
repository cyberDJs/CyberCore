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
