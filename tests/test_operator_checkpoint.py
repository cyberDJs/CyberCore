from dataclasses import replace
import pytest

from cybercore.operator_checkpoint import checkpoint_operator_update
from cybercore.operator_reporting import OperatorUpdate


def event(**changes: object) -> OperatorUpdate:
    values = {
        "event_kind": "review_finding",
        "subject": "CyberCore PR #164",
        "sha": "a" * 40,
        "state": "BLOCKED",
        "what": "Code review našel P2",
        "why": "Chybí ověřená vazba na původ",
        "impact": "Žádná změna runtime; merge pozastaven",
        "next_action": "Opravit izolovaný test",
        "evidence_url": "https://github.com/cyberDJs/CyberCore/pull/164",
        "approval_required": False,
        "changed": True,
    }
    values.update(changes)
    return OperatorUpdate(**values)  # type: ignore[arg-type]


def test_first_material_event_includes_report_and_digest() -> None:
    decision = checkpoint_operator_update(event())
    assert decision.reason == "MATERIAL_CHANGE"
    assert decision.report is not None
    assert "Dopad:" in decision.report
    assert decision.fingerprint is not None
    assert len(decision.fingerprint) == 64


def test_same_delivered_event_is_suppressed() -> None:
    first = checkpoint_operator_update(event())
    second = checkpoint_operator_update(event(), last_delivered_fingerprint=first.fingerprint)
    assert second.reason == "UNCHANGED"
    assert second.report is None
    assert second.fingerprint == first.fingerprint


def test_changed_impact_or_security_finding_is_not_suppressed() -> None:
    prior = checkpoint_operator_update(event()).fingerprint
    newer = checkpoint_operator_update(
        event(impact="Blokuje schválení bezpečnosti"),
        last_delivered_fingerprint=prior,
    )
    assert newer.reason == "MATERIAL_CHANGE"
    assert newer.report is not None
    assert newer.fingerprint != prior


def test_non_material_event_does_not_replace_last_delivered_checkpoint() -> None:
    prior = checkpoint_operator_update(event()).fingerprint
    decision = checkpoint_operator_update(event(changed=False), last_delivered_fingerprint=prior)
    assert decision.reason == "NON_MATERIAL"
    assert decision.fingerprint is None
    assert decision.report is None


@pytest.mark.parametrize("invalid", ("", "nope", "a" * 63, "G" * 64, 123))
def test_invalid_prior_fingerprint_is_rejected(invalid: object) -> None:
    with pytest.raises(ValueError, match="INVALID_CHECKPOINT"):
        checkpoint_operator_update(
            event(),
            last_delivered_fingerprint=invalid,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid", ("false", 1, None))
def test_non_boolean_changed_flag_fails_closed(invalid: object) -> None:
    with pytest.raises(ValueError, match="INVALID_CHANGED_FLAG"):
        checkpoint_operator_update(
            replace(event(), changed=invalid)  # type: ignore[arg-type]
        )


def test_missing_evidence_never_creates_a_checkpoint() -> None:
    with pytest.raises(ValueError, match="INVALID_EVIDENCE_URL"):
        checkpoint_operator_update(event(evidence_url="https://example.com/not-evidence"))


def test_different_full_text_after_display_cutoff_is_not_suppressed() -> None:
    original = event(impact="A" * 240 + "first")
    modified = event(impact="A" * 240 + "second")
    prior = checkpoint_operator_update(original)
    later = checkpoint_operator_update(
        modified, last_delivered_fingerprint=prior.fingerprint
    )
    assert prior.report == later.report
    assert later.reason == "MATERIAL_CHANGE"
    assert later.fingerprint != prior.fingerprint


def test_different_full_sha_after_display_prefix_is_not_suppressed() -> None:
    original = event(sha="a" * 40)
    modified = event(sha="a" * 12 + "b" * 28)
    prior = checkpoint_operator_update(original)
    later = checkpoint_operator_update(
        modified, last_delivered_fingerprint=prior.fingerprint
    )
    assert prior.report == later.report
    assert later.reason == "MATERIAL_CHANGE"
    assert later.fingerprint != prior.fingerprint


@pytest.mark.parametrize(
    "bad_fields,reason",
    (
        ({"sha": "bad"}, "INVALID_SHA"),
        ({"state": "PASS"}, "INVALID_STATE"),
        ({"approval_required": "true"}, "INVALID_APPROVAL_FLAG"),
        ({"evidence_url": "https://example.invalid"}, "INVALID_EVIDENCE_URL"),
        ({"subject": ""}, "EMPTY_DISPLAY_TEXT"),
        ({"what": 17}, "INVALID_DISPLAY_TEXT"),
        ({"event_kind": None}, "INVALID_EVENT_KIND"),
    ),
)
def test_invalid_nonmaterial_event_fails_closed(
    bad_fields: dict[str, object], reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        checkpoint_operator_update(event(changed=False, **bad_fields))


def test_invalid_unknown_event_kind_does_not_bypass_shape_validation() -> None:
    with pytest.raises(ValueError, match="INVALID_SHA"):
        checkpoint_operator_update(event(event_kind="unrecognized", sha="bad"))
