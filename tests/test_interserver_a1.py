from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path

import pytest

from cybercore.interserver_a1 import (
    A1ProbeError,
    PASSWORD_DIGITS,
    PASSWORD_LOWER,
    PASSWORD_SPECIALS,
    PASSWORD_UPPER,
    build_quote_payload,
    safe_catalog_receipt,
    sanitize_quote,
    select_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG_FIXTURE = ROOT / "tests/fixtures/interserver-vps-catalog.synthetic.json"
QUOTE_FIXTURE = ROOT / "tests/fixtures/interserver-vps-quote-response.synthetic.json"


def _load(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_select_candidate_enforces_wb0035_bounds() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))

    assert candidate.platform == "kvm"
    assert candidate.slices == 1
    assert candidate.os_distro == "ubuntu"
    assert candidate.os_version == "ubuntu24"
    assert candidate.control_panel == "none"
    assert candidate.location_id == 1
    assert candidate.location_name == "New Jersey"
    assert candidate.currency == "USD"
    assert candidate.catalog_price_month == Decimal("3")
    assert candidate.ram_mib == 2048
    assert candidate.disk_gib == 40
    assert candidate.transfer_gib == 2000


def test_catalog_uses_kvm_slice_price_not_vps_ny_cost() -> None:
    catalog = copy.deepcopy(_load(CATALOG_FIXTURE))
    catalog["vpsSliceKvmLCost"] = 3
    catalog["vpsNyCost"] = 1

    candidate = select_candidate(catalog)
    receipt = safe_catalog_receipt(candidate)

    assert candidate.catalog_price_month == Decimal("3")
    assert receipt["catalog_price_field"] == "vpsSliceKvmLCost"


def test_quote_payload_uses_only_a1_validation_shape() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    payload = build_quote_payload(candidate)

    assert payload["vpsPlatform"] == "kvm"
    assert payload["slices"] == 1
    assert payload["osDistro"] == "ubuntu"
    assert payload["osVersion"] == "ubuntu24"
    assert payload["controlpanel"] == "none"
    assert payload["hostname"] == "tasks.cyberdjs.org"
    assert isinstance(payload["rootpass"], str)
    rootpass = payload["rootpass"]
    assert len(rootpass) >= 32
    assert any(char in PASSWORD_LOWER for char in rootpass)
    assert any(char in PASSWORD_UPPER for char in rootpass)
    assert any(char in PASSWORD_DIGITS for char in rootpass)
    assert any(char in PASSWORD_SPECIALS for char in rootpass)
    assert "order" not in payload
    assert "payment" not in payload


def test_sanitize_quote_drops_secret_and_customer_fields() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = _load(QUOTE_FIXTURE)

    sanitized = sanitize_quote(candidate, raw_quote)
    rendered = json.dumps(sanitized, sort_keys=True)

    assert sanitized["evidence_mode"] == "LIVE_READ_ONLY"
    assert sanitized["recurring_price_usd_month"] == "3.00"
    assert sanitized["one_time_price_usd"] == "0.00"
    assert sanitized["location_id"] == 1
    assert sanitized["location_name"] == "New Jersey"
    assert sanitized["order_performed"] is False
    assert sanitized["payment_performed"] is False
    assert sanitized["secret_values_recorded"] is False
    assert "rootpass" not in rendered.lower()
    assert "SYNTHETIC_SECRET_MUST_NOT_ESCAPE" not in rendered
    assert "custid" not in rendered.lower()
    assert "123456" not in rendered


def test_live_quote_os_version_field_mapping_is_enforced() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = copy.deepcopy(_load(QUOTE_FIXTURE))
    raw_quote["os"] = "ubuntu"
    raw_quote["version"] = "ubuntu24"

    with pytest.raises(A1ProbeError, match="mismatch"):
        sanitize_quote(candidate, raw_quote)


def test_catalog_above_budget_fails_closed() -> None:
    catalog = copy.deepcopy(_load(CATALOG_FIXTURE))
    catalog["vpsSliceKvmLCost"] = 3.01

    with pytest.raises(A1ProbeError, match="monthly ceiling"):
        select_candidate(catalog)


def test_catalog_fractional_cent_fails_closed() -> None:
    catalog = copy.deepcopy(_load(CATALOG_FIXTURE))
    catalog["vpsSliceKvmLCost"] = "2.994"

    with pytest.raises(A1ProbeError, match="fractional-cent"):
        select_candidate(catalog)


def test_catalog_nonpositive_kvm_price_fails_closed() -> None:
    catalog = copy.deepcopy(_load(CATALOG_FIXTURE))
    catalog["vpsSliceKvmLCost"] = 0

    with pytest.raises(A1ProbeError, match="must be positive"):
        select_candidate(catalog)


def test_catalog_without_ubuntu24_fails_closed() -> None:
    catalog = copy.deepcopy(_load(CATALOG_FIXTURE))
    templates = catalog["templates"]
    assert isinstance(templates, dict)
    kvm = templates["kvm"]
    assert isinstance(kvm, dict)
    ubuntu = kvm["ubuntu"]
    assert isinstance(ubuntu, dict)
    ubuntu.pop("ubuntu24")

    with pytest.raises(A1ProbeError, match="Ubuntu 24"):
        select_candidate(catalog)


def test_quote_above_budget_fails_closed() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = copy.deepcopy(_load(QUOTE_FIXTURE))
    raw_quote["service_cost"] = 4
    raw_quote["monthly_service_cost"] = 4

    with pytest.raises(A1ProbeError, match="monthly ceiling"):
        sanitize_quote(candidate, raw_quote)


def test_quote_fractional_cent_fails_closed_before_rounding() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = copy.deepcopy(_load(QUOTE_FIXTURE))
    raw_quote["service_cost"] = "2.994"
    raw_quote["monthly_service_cost"] = "2.994"

    with pytest.raises(A1ProbeError, match="fractional-cent"):
        sanitize_quote(candidate, raw_quote)


def test_quote_unexpected_one_time_charge_fails_closed() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = copy.deepcopy(_load(QUOTE_FIXTURE))
    raw_quote["service_cost"] = "3.01"
    raw_quote["monthly_service_cost"] = "3.00"

    with pytest.raises(A1ProbeError, match="one-time charge"):
        sanitize_quote(candidate, raw_quote)


def test_quote_configuration_mismatch_fails_closed() -> None:
    candidate = select_candidate(_load(CATALOG_FIXTURE))
    raw_quote = copy.deepcopy(_load(QUOTE_FIXTURE))
    raw_quote["platform"] = "hyperv"

    with pytest.raises(A1ProbeError, match="mismatch"):
        sanitize_quote(candidate, raw_quote)
