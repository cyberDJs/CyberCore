from __future__ import annotations

import pytest

from cybercore.interserver_inventory import InventoryFormatError, summarize_vps_inventory


def test_empty_inventory() -> None:
    assert summarize_vps_inventory({"services": []}) == {
        "source": "interserver",
        "verified_provider_response": False,
        "total_vps": 0,
        "by_status": {},
    }


def test_counts_normalized_without_exposing_sensitive_fields() -> None:
    payload = {"services": [
        {"status": "Active", "ip": "192.0.2.1", "api_key": "sensitive"},
        {"status": "running", "hostname": "private.example", "customer": "private"},
        {"status": "Stopped", "invoice": "private"},
    ]}
    result = summarize_vps_inventory(payload)
    assert result["total_vps"] == 3
    assert result["by_status"] == {"active": 1, "running": 1, "stopped": 1}
    text = repr(result)
    for secret in ("192.0.2.1", "sensitive", "private.example", "invoice"):
        assert secret not in text


@pytest.mark.parametrize("payload", [
    None,
    {"unexpected": []},
    {"services": "wrong"},
    {"services": [{}]},
    {"services": [{"status": None}]},
    {"services": [{"status": "unreviewed-status"}]},
    {"services": [1]},
])
def test_rejects_ambiguous_provider_responses(payload: object) -> None:
    with pytest.raises(InventoryFormatError):
        summarize_vps_inventory(payload)
