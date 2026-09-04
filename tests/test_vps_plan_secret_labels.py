from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.vps_plan import prepare_purchase_approval_packet

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / ".cybercore/provisioning/interserver-vps-plan.example.yaml"
SYNTHETIC_QUOTE = ROOT / "tests/fixtures/interserver-vps-quote.synthetic.yaml"


def _live_quote_text() -> str:
    return (
        SYNTHETIC_QUOTE.read_text(encoding="utf-8")
        .replace("evidence_mode: SYNTHETIC_FIXTURE", "evidence_mode: LIVE_READ_ONLY")
        .replace("provider_contact_performed: false", "provider_contact_performed: true")
        .replace("quote_reference: SYNTHETIC-WB0035", "quote_reference: LIVE-QUOTE-001")
    )


@pytest.mark.parametrize(
    "label",
    (
        "password",
        "rootpass",
        "api_key",
        "x-api-key",
        "private_key",
        "totp_seed",
        "recovery_code",
        "session_cookie",
    ),
)
@pytest.mark.parametrize("separator", (":", "="))
def test_all_secret_labels_reject_both_separators_with_whitespace(
    tmp_path: Path, label: str, separator: str
) -> None:
    quote = tmp_path / "quote.yaml"
    literal = f"{label} {separator} provider-secret"
    quote.write_text(
        _live_quote_text().replace(
            "quote_reference: LIVE-QUOTE-001",
            f'quote_reference: "{literal}"',
        ),
        encoding="utf-8",
    )

    result, packet = prepare_purchase_approval_packet(PLAN, quote)

    assert not result.ok
    assert packet is None
    assert any("secret-like literal" in error for error in result.errors)
