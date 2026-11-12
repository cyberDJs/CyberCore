from dataclasses import replace

import pytest

from cybercore.operator_reporting import OperatorUpdate, format_operator_update


def sample(**changes: object) -> OperatorUpdate:
    values = dict(
        event_kind="checks_failed",
        subject="CyberCore PR #159",
        sha="a" * 40,
        state="BLOCKED",
        what="CodeQL nedokončeno",
        why="Kontrola ještě nemá doložený výsledek",
        impact="Nemění uživatelské funkce; merge čeká",
        next_action="Ověřit výsledky pro přesný HEAD",
        evidence_url="https://github.com/cyberDJs/CyberCore/pull/159",
        approval_required=False,
        changed=True,
    )
    values.update(changes)
    return OperatorUpdate(**values)  # type: ignore[arg-type]


def test_material_event_includes_cause_impact_next_action_and_evidence() -> None:
    text = format_operator_update(sample())
    assert text is not None
    assert "BLOCKED" in text
    for label in ("Co:", "Proč:", "Dopad:", "Dál:", "Souhlas:", "Důkaz:"):
        assert label in text
    assert "a" * 12 in text
    assert "nyní není nutný" in text


def test_repeated_or_nonmaterial_events_generate_no_report() -> None:
    assert format_operator_update(sample(changed=False)) is None
    assert format_operator_update(sample(event_kind="no_change")) is None


def test_explicit_approval_renders_as_human_gate_not_an_action() -> None:
    text = format_operator_update(
        sample(event_kind="approval_required", approval_required=True, state="BLOCKED")
    )
    assert text is not None
    assert "Souhlas: vyžadován" in text


@pytest.mark.parametrize(
    "field,value,reason",
    (
        ("sha", "short", "INVALID_SHA"),
        ("state", "PASSED", "INVALID_STATE"),
        ("evidence_url", "https://example.invalid/unknown", "INVALID_EVIDENCE_URL"),
        ("approval_required", "yes", "INVALID_APPROVAL_FLAG"),
    ),
)
def test_invalid_fields_fail_closed(field: str, value: object, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        format_operator_update(replace(sample(), **{field: value}))


def test_untrusted_multiline_text_is_compacted_for_one_screen() -> None:
    text = format_operator_update(sample(impact="Funkce    zatím\n  beze změny"))
    assert text is not None
    assert "Dopad: Funkce zatím beze změny" in text


def test_no_automatic_main_push_success_claim_from_unknown_state() -> None:
    text = format_operator_update(
        sample(
            state="UNKNOWN",
            what="Main-push kontrola není přes dostupné API ověřitelná",
            why="Konektor ukazuje pouze PR-triggered běhy",
        )
    )
    assert text is not None
    assert "UNKNOWN" in text
    assert "Main-push kontrola není" in text
