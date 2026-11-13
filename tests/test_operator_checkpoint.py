from dataclasses import replace
from hashlib import sha256

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
    assert decision.fingerprint == sha256(decision.report.encode("utf-8")).hexdigest()


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
