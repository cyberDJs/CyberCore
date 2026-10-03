from __future__ import annotations

from pathlib import Path

from cybercore.vps_plan import validate_plan_and_quote, validate_vps_quote

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / ".cybercore/provisioning/interserver-vps-plan.example.yaml"
SYNTHETIC_QUOTE = ROOT / "tests/fixtures/interserver-vps-quote.synthetic.yaml"


def _quote_with_oversized_integer() -> str:
    oversized = "9" * 5000
    return SYNTHETIC_QUOTE.read_text(encoding="utf-8").replace(
        "recurring_price_usd_month: 3.00",
        f"recurring_price_usd_month: {oversized}",
    )


def test_oversized_yaml_integer_fails_closed_in_quote_validation(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(_quote_with_oversized_integer(), encoding="utf-8")

    result = validate_vps_quote(quote)

    assert not result.ok
    assert any("invalid YAML" in error for error in result.errors)


def test_oversized_yaml_integer_fails_closed_in_plan_quote_validation(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(_quote_with_oversized_integer(), encoding="utf-8")

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("invalid YAML" in error for error in result.errors)
