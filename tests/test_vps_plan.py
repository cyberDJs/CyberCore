from __future__ import annotations

from pathlib import Path

from cybercore.vps_plan import (
    prepare_purchase_approval_packet,
    validate_plan_and_quote,
    validate_vps_plan,
    validate_vps_quote,
)

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


def test_plan_is_valid_and_fail_closed() -> None:
    result = validate_vps_plan(PLAN)
    assert result.ok, result.as_text()
    text = PLAN.read_text(encoding="utf-8")
    assert "provider_contact_allowed: false" in text
    assert "order_allowed: false" in text
    assert "payment_allowed: false" in text
    assert "dns_mutation_allowed: false" in text
    assert "ssh_mutation_allowed: false" in text
    assert "application_deploy_allowed: false" in text
    assert "location_id: 1" in text
    assert "location_name: New Jersey" in text


def test_synthetic_quote_is_valid_but_not_purchase_evidence() -> None:
    result = validate_vps_quote(SYNTHETIC_QUOTE)
    assert result.ok, result.as_text()
    assert "synthetic quote cannot be used as purchase evidence" in result.warnings

    packet_result, packet = prepare_purchase_approval_packet(PLAN, SYNTHETIC_QUOTE)
    assert not packet_result.ok
    assert packet is None
    assert any("LIVE_READ_ONLY" in error for error in packet_result.errors)


def test_live_quote_can_prepare_non_authorizing_approval_packet(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(_live_quote_text(), encoding="utf-8")

    result, packet = prepare_purchase_approval_packet(PLAN, quote)

    assert result.ok, result.as_text()
    assert packet is not None
    assert packet.public_hostname == "tasks.cyberdjs.org"
    assert packet.location_id == 1
    assert packet.location_name == "New Jersey"
    assert packet.recurring_price_usd_month == "3.00"
    assert packet.purchase_authorized is False
    assert packet.payment_authorized is False
    assert packet.requires_explicit_approval is True


def test_quote_over_monthly_budget_is_blocked(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text().replace(
            "recurring_price_usd_month: 3.00", "recurring_price_usd_month: 3.01"
        ),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("exceeds monthly budget ceiling" in error for error in result.errors)


def test_subcent_quote_amount_is_rejected(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text().replace(
            "recurring_price_usd_month: 3.00", "recurring_price_usd_month: 2.994"
        ),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("whole-cent recurring_price_usd_month" in error for error in result.errors)


def test_unexpected_one_time_charge_is_blocked(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text().replace("one_time_price_usd: 0.00", "one_time_price_usd: 1.00"),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("exceeds one-time budget ceiling" in error for error in result.errors)


def test_quote_below_resource_floor_is_blocked(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text()
        .replace("ram_mib: 2048", "ram_mib: 1024")
        .replace("disk_gib: 40", "disk_gib: 20"),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("resources.ram_mib" in error for error in result.errors)
    assert any("resources.disk_gib" in error for error in result.errors)


def test_quote_cannot_claim_order_or_payment(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text()
        .replace("order_performed: false", "order_performed: true")
        .replace("payment_performed: false", "payment_performed: true"),
        encoding="utf-8",
    )

    result = validate_vps_quote(quote)

    assert not result.ok
    assert any("order_performed" in error for error in result.errors)
    assert any("payment_performed" in error for error in result.errors)


def test_plan_rejects_authority_escalation(tmp_path: Path) -> None:
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        PLAN.read_text(encoding="utf-8")
        .replace("provider_contact_allowed: false", "provider_contact_allowed: true")
        .replace("order_allowed: false", "order_allowed: true"),
        encoding="utf-8",
    )

    result = validate_vps_plan(plan)

    assert not result.ok
    assert any("provider_contact_allowed" in error for error in result.errors)
    assert any("order_allowed" in error for error in result.errors)


def test_duplicate_yaml_key_is_rejected(tmp_path: Path) -> None:
    plan = tmp_path / "plan.yaml"
    plan.write_text("provider: Evil\n" + PLAN.read_text(encoding="utf-8"), encoding="utf-8")

    result = validate_vps_plan(plan)

    assert not result.ok
    assert any("duplicate YAML key: provider" in error for error in result.errors)


def test_explicit_yaml_merge_tag_is_rejected(tmp_path: Path) -> None:
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        PLAN.read_text(encoding="utf-8").replace("authority:\n", "authority:\n  !!merge foo: {}\n"),
        encoding="utf-8",
    )

    result = validate_vps_plan(plan)

    assert not result.ok
    assert any("forbids YAML merge keys" in error for error in result.errors)


def test_recursive_alias_is_rejected_without_recursing(tmp_path: Path) -> None:
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        PLAN.read_text(encoding="utf-8") + "recursive: &loop {child: *loop}\n",
        encoding="utf-8",
    )

    result = validate_vps_plan(plan)

    assert not result.ok
    assert any("forbids YAML anchors" in error for error in result.errors)
    assert any("forbids YAML aliases" in error for error in result.errors)


def test_secret_like_literal_is_rejected(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(_live_quote_text() + "\npassword: nope\n", encoding="utf-8")

    result = validate_vps_quote(quote)

    assert not result.ok
    assert any("secret-like literal" in error for error in result.errors)


def test_decoded_secret_like_literal_is_rejected(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text().replace(
            "quote_reference: LIVE-QUOTE-001",
            'quote_reference: "password\\x3dsekrit"',
        ),
        encoding="utf-8",
    )

    result = validate_vps_quote(quote)

    assert not result.ok
    assert any("secret-like literal" in error for error in result.errors)


def test_quote_must_match_tasks_hostname(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text().replace("tasks.cyberdjs.org", "tasks.eimyherrer.com"),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("public_hostname" in error for error in result.errors)


def test_quote_location_is_bound(tmp_path: Path) -> None:
    quote = tmp_path / "quote.yaml"
    quote.write_text(
        _live_quote_text()
        .replace("location_id: 1", "location_id: 2")
        .replace("location_name: New Jersey", "location_name: Los Angeles"),
        encoding="utf-8",
    )

    result = validate_plan_and_quote(PLAN, quote)

    assert not result.ok
    assert any("location_id" in error or "location_name" in error for error in result.errors)
