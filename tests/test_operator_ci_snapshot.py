from dataclasses import replace

import pytest

from cybercore.caser41_github_snapshot import Job, Workflow
from cybercore.operator_checkpoint import checkpoint_operator_update
from cybercore.operator_ci_snapshot import ci_snapshot_operator_update
from cybercore.operator_reporting import format_operator_update

SHA = "a" * 40
RUNS = (
    Workflow(101, "CI", "completed", "success"),
    Workflow(102, "CodeQL", "completed", "success"),
    Workflow(103, "Action Kernel real CyberHIVE contract", "completed", "success"),
)
JOBS = (
    Job(101, 1, "quality", "completed", "success"),
    Job(101, 2, "package", "completed", "success"),
    Job(101, 3, "tests (python 3.11)", "completed", "success"),
    Job(101, 4, "tests (python 3.12)", "completed", "success"),
    Job(101, 5, "tests (python 3.13)", "completed", "success"),
    Job(101, 6, "tests (python 3.14)", "completed", "success"),
    Job(102, 7, "codeql", "completed", "success"),
    Job(103, 8, "real-hive-contract", "completed", "success"),
)


def make(**kwargs: object):
    args = dict(
        pr_number=165,
        provider_pr_number=165,
        expected_sha=SHA,
        provider_head_sha=SHA,
        workflows=RUNS,
        jobs=JOBS,
        changed=True,
    )
    args.update(kwargs)
    return ci_snapshot_operator_update(**args)  # type: ignore[arg-type]


def test_structurally_consistent_ci_is_unknown_never_pass() -> None:
    update = make()
    assert update.state == "UNKNOWN"
    assert update.event_kind == "critical_evidence_missing"
    report = format_operator_update(update)
    assert report is not None
    assert "UNKNOWN" in report
    assert "Nelze potvrdit PASS" in report
    assert "https://github.com/cyberDJs/CyberCore/pull/165" in report


@pytest.mark.parametrize(
    "changes,reason",
    (
        ({"provider_head_sha": "b" * 40}, "HEAD_DRIFT"),
        ({"workflows": RUNS[:-1]}, "MISSING_WORKFLOW"),
        ({"jobs": JOBS[:-1]}, "MISSING_JOB"),
        (
            {"jobs": JOBS[:2] + (replace(JOBS[2], conclusion="failure"),) + JOBS[3:]},
            "JOB_NOT_SUCCESSFUL",
        ),
    ),
)
def test_bad_or_stale_ci_is_blocked(changes: dict[str, object], reason: str) -> None:
    update = make(**changes)
    assert update.state == "BLOCKED"
    assert update.event_kind == ("source_drift" if reason == "HEAD_DRIFT" else "checks_failed")
    assert reason in (format_operator_update(update) or "")


def test_repeating_same_cautious_report_is_suppressed() -> None:
    first = checkpoint_operator_update(make())
    assert first.reason == "MATERIAL_CHANGE"
    second = checkpoint_operator_update(make(), last_delivered_fingerprint=first.fingerprint)
    assert second.reason == "UNCHANGED"
    assert second.report is None


def test_new_pr_identity_changes_checkpoint() -> None:
    first = checkpoint_operator_update(make())
    updated = checkpoint_operator_update(
        make(pr_number=166, provider_pr_number=166),
        last_delivered_fingerprint=first.fingerprint,
    )
    assert updated.reason == "MATERIAL_CHANGE"
    assert updated.fingerprint != first.fingerprint


def test_new_head_cannot_reuse_old_consistent_snapshot() -> None:
    # A previously cached result is no longer accepted as an input.
    # The observed head must be checked within the bound reconciliation.
    changed = make(expected_sha="b" * 40)
    assert changed.state == "BLOCKED"
    assert changed.event_kind == "source_drift"


@pytest.mark.parametrize(
    "changes,reason",
    (
        ({"pr_number": True}, "INVALID_PR_NUMBER"),
        ({"pr_number": 0}, "INVALID_PR_NUMBER"),
        ({"pr_number": "165"}, "INVALID_PR_NUMBER"),
        ({"provider_pr_number": 164}, "PR_IDENTITY_DRIFT"),
        ({"provider_pr_number": True}, "PR_IDENTITY_DRIFT"),
        ({"expected_sha": "not-sha"}, "INVALID_SHA"),
        ({"changed": "false"}, "INVALID_CHANGED_FLAG"),
    ),
)
def test_invalid_identity_or_flags_fail_closed(changes: dict[str, object], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        make(**changes)


def test_bad_provider_shape_never_promoted_to_success() -> None:
    for update in (make(workflows=()), make(jobs=None), make(provider_head_sha="bad")):
        assert update.state == "BLOCKED"


def test_caller_changed_false_cannot_silence_critical_evidence() -> None:
    unknown = make(changed=False)
    assert unknown.state == "UNKNOWN"
    assert unknown.changed is True
    assert "UNKNOWN" in (format_operator_update(unknown) or "")
    blocked_cases = (
        {"provider_head_sha": "b" * 40},
        {"workflows": RUNS[:-1]},
        {"jobs": JOBS[:-1]},
        {"jobs": JOBS[:2] + (replace(JOBS[2], conclusion="failure"),) + JOBS[3:]},
    )
    for case in blocked_cases:
        blocked = make(changed=False, **case)
        assert blocked.state == "BLOCKED"
        assert blocked.changed is True
        assert "BLOCKED" in (format_operator_update(blocked) or "")


def test_critical_report_is_suppressed_only_after_checkpoint_ack() -> None:
    blocked = make(changed=False, provider_head_sha="b" * 40)
    first = checkpoint_operator_update(blocked)
    assert first.reason == "MATERIAL_CHANGE"
    assert first.report is not None
    assert "BLOCKED" in first.report
    assert first.fingerprint is not None
    retry_without_ack = checkpoint_operator_update(blocked)
    assert retry_without_ack.reason == "MATERIAL_CHANGE"
    after_ack = checkpoint_operator_update(blocked, last_delivered_fingerprint=first.fingerprint)
    assert after_ack.reason == "UNCHANGED"
    assert after_ack.report is None


def test_caller_cannot_supply_detached_cached_reconciliation() -> None:
    from cybercore.caser41_github_snapshot import Reconciliation

    with pytest.raises(TypeError):
        make(
            snapshot=Reconciliation("CONSISTENT_ONLY", "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED")
        )
