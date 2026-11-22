from __future__ import annotations

import io
import urllib.error

import pytest

from cybercore.interserver_provider import (
    InterServerInventoryError,
    fetch_vps_inventory,
    summarize_provider_rows,
)


class FakeResponse:
    def __init__(self, payload: bytes, code: int = 200) -> None:
        self.data = io.BytesIO(payload)
        self.code = code

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.data.close()

    def getcode(self) -> int:
        return self.code

    def read(self, size: int = -1) -> bytes:
        return self.data.read(size)


def test_summary_omits_customer_and_credentials() -> None:
    data = [
        {
            "vps_id": 1,
            "vps_status": "active",
            "repeat_invoices_cost": "6.00",
            "password": "never-show",
            "hostname": "hidden.example",
        },
        {"vps_id": 2, "vps_status": "pending", "repeat_invoices_cost": "8"},
    ]
    result = summarize_provider_rows(data)
    assert result["total_vps"] == 2
    assert result["by_status"] == {"active": 1, "pending": 1}
    assert result["listed_recurring_cost_by_status"] == {
        "active": "6.00",
        "pending": "8",
    }
    assert result["billing_verified"] is False
    assert "never-show" not in repr(result)
    assert "hidden.example" not in repr(result)


def test_request_uses_allowlisted_endpoint_and_secret_header() -> None:
    def opener(request: object, timeout: int) -> FakeResponse:
        assert request.full_url == "https://my.interserver.net/apiv2/vps"
        assert request.get_method() == "GET"
        assert request.get_header("X-api-key") == "test-key"
        assert timeout == 10
        return FakeResponse(b'[{"vps_id":1,"vps_status":"active","repeat_invoices_cost":"6"}]')

    result = fetch_vps_inventory("test-key", opener=opener)
    assert result["total_vps"] == 1
    assert "test-key" not in repr(result)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [{"vps_id": 1, "vps_status": "active"}],
        [{"vps_id": 1, "vps_status": "unexpected", "repeat_invoices_cost": 6}],
        [{"vps_id": 1, "vps_status": "active", "repeat_invoices_cost": "-1"}],
        [{"vps_id": 1, "vps_status": "active", "repeat_invoices_cost": "NaN"}],
        [
            {"vps_id": 1, "vps_status": "active", "repeat_invoices_cost": "1"},
            {"vps_id": 1, "vps_status": "active", "repeat_invoices_cost": "1"},
        ],
    ],
)
def test_rejects_ambiguous_or_unsafe_rows(payload: object) -> None:
    with pytest.raises(InterServerInventoryError):
        summarize_provider_rows(payload)


@pytest.mark.parametrize("body", [b"not JSON", b"{}", b"null"])
def test_bad_json_or_envelope_never_exposes_response(body: bytes) -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        return FakeResponse(body)

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert "secret" not in str(error.value)
    assert "not JSON" not in str(error.value)


def test_http_failure_never_exposes_provider_error() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        raise urllib.error.HTTPError(
            "https://my.interserver.net/apiv2/vps", 403, "secret leaked", {}, None
        )

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert "secret" not in str(error.value)


def test_rejects_large_response() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        return FakeResponse(b"x" * (1024 * 1024 + 1))

    with pytest.raises(InterServerInventoryError, match="too large"):
        fetch_vps_inventory("secret", opener=opener)
