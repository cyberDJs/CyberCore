from dataclasses import replace

import pytest

from cybercore.caser41_github_snapshot import Reconciliation
from cybercore.operator_checkpoint import checkpoint_operator_update
from cybercore.operator_ci_snapshot import ci_snapshot_operator_update
from cybercore.operator_reporting import format_operator_update

SHA = "a" * 40
STRUCTURAL_ONLY = Reconciliation("CONSISTENT_ONLY", "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED")


def make(
    snapshot: Reconciliation = STRUCTURAL_ONLY,
    **kwargs: object,
):
    inputs = dict(pr_number=164, expected_sha=SHA, snapshot=snapshot, changed=True)
    inputs.update(kwargs)
    return ci_snapshot_operator_update(**inputs)  # type: ignore[arg-type]


def test_consistent_snapshot_is_unknown_never_pass_or_merge_ready() -> None:
    update = make()
    assert update.state == "UNKNOWN"
    assert update.event_kind == "critical_evidence_missing"
    report = format_operator_update(update)
    assert report is not None
    assert "UNKNOWN" in report
    assert "Nelze potvrdit PASS" in report
    assert "https://github.com/cyberDJs/CyberCore/pull/164" in report


@pytest.mark.parametrize("reason", ("HEAD_DRIFT", "MISSING_WORKFLOW", "JOB_NOT_SUCCESSFUL"))
def test_failed_snapshot_never_gets_pass(reason: str) -> None:
    update = make(Reconciliation("BLOCKED", reason))
    assert update.state == "BLOCKED"
    assert update.event_kind == ("source_drift" if reason == "HEAD_DRIFT" else "checks_failed")
    assert reason in (format_operator_update(update) or "")


def test_repeating_same_cautious_report_is_suppressed() -> None:
    first = checkpoint_operator_update(make())
    assert first.reason == "MATERIAL_CHANGE"
    second = checkpoint_operator_update(make(), last_delivered_fingerprint=first.fingerprint)
    assert second.reason == "UNCHANGED"
    assert second.report is None


def test_new_exact_sha_changes_checkpoint_without_changing_short_message() -> None:
    first = checkpoint_operator_update(make())
    updated = checkpoint_operator_update(
        make(expected_sha="b" * 40), last_delivered_fingerprint=first.fingerprint
    )
    assert updated.reason == "MATERIAL_CHANGE"
    assert updated.fingerprint != first.fingerprint


@pytest.mark.parametrize(
    "inputs,reason",
    (
        ({"pr_number": True}, "INVALID_PR_NUMBER"),
        ({"pr_number": 0}, "INVALID_PR_NUMBER"),
        ({"pr_number": "164"}, "INVALID_PR_NUMBER"),
        ({"expected_sha": "not-sha"}, "INVALID_SHA"),
        ({"changed": "false"}, "INVALID_CHANGED_FLAG"),
        ({"snapshot": None}, "INVALID_RECONCILIATION"),
        ({"snapshot": Reconciliation("VERIFIED", "OK")}, "INVALID_RECONCILIATION"),
        ({"snapshot": Reconciliation("CONSISTENT_ONLY", "SUCCESS")}, "INVALID_RECONCILIATION"),
        ({"snapshot": Reconciliation("BLOCKED", "secret=token")}, "INVALID_RECONCILIATION"),
    ),
)
def test_invalid_untrusted_inputs_fail_closed(inputs: dict[str, object], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        make(**inputs)


def test_nonmaterial_event_is_still_structurally_validated() -> None:
    event = make(changed=False)
    assert format_operator_update(event) is None
    with pytest.raises(ValueError, match="INVALID_RECONCILIATION"):
        make(changed=False, snapshot=replace(STRUCTURAL_ONLY, status="PASS"))
