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
        [{"vps_id": 1, "vps_status": "", "repeat_invoices_cost": 6}],
        [{"vps_id": 1, "vps_status": None, "repeat_invoices_cost": 6}],
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


def test_http_status_is_numeric_and_provider_text_is_never_in_diagnostic() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        raise urllib.error.HTTPError(
            "https://my.interserver.net/apiv2/vps?secret=hidden",
            403,
            "secret leaked by upstream",
            {},
            None,
        )

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("very-secret", opener=opener)
    assert error.value.category == "http_error"
    assert error.value.http_status == 403
    assert "very-secret" not in str(error.value)
    assert "hidden" not in str(error.value)
    assert "secret leaked by upstream" not in str(error.value)


def test_unexpected_response_http_status_is_classified() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        return FakeResponse(b"private error body", code=503)

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert error.value.category == "http_error"
    assert error.value.http_status == 503


def test_invalid_json_has_safe_category() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        return FakeResponse(b"not JSON: secret response")

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert error.value.category == "invalid_json"


def test_schema_error_has_safe_category() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        return FakeResponse(b'{"private": "hidden"}')

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert error.value.category == "schema_envelope"
    assert "hidden" not in str(error.value)


def test_network_error_has_safe_category() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        raise urllib.error.URLError("private endpoint details")

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert error.value.category == "network_error"
    assert "private endpoint details" not in str(error.value)


def test_timeout_has_safe_category() -> None:
    def opener(_request: object, timeout: int) -> FakeResponse:
        raise TimeoutError("private timeout details")

    with pytest.raises(InterServerInventoryError) as error:
        fetch_vps_inventory("secret", opener=opener)
    assert error.value.category == "timeout"
    assert "private timeout details" not in str(error.value)


@pytest.mark.parametrize(
    ("payload", "expected_category"),
    [
        ({}, "schema_envelope"),
        ([1], "schema_row"),
        ([{"vps_status": "active", "repeat_invoices_cost": "2"}], "schema_id"),
        (
            [{"vps_id": 1, "vps_status": None, "repeat_invoices_cost": "2"}],
            "schema_status",
        ),
        ([{"vps_id": 1, "vps_status": "active"}], "schema_cost_missing"),
        (
            [
                {
                    "vps_id": 1,
                    "vps_status": "active",
                    "repeat_invoices_cost": "private-value",
                }
            ],
            "schema_cost_invalid",
        ),
    ],
)
def test_schema_diagnostics_are_fixed_and_do_not_expose_values(
    payload: object, expected_category: str
) -> None:
    with pytest.raises(InterServerInventoryError) as error:
        summarize_provider_rows(payload)
    assert error.value.category == expected_category
    assert "private" not in str(error.value)
    assert "private" not in error.value.category


def test_unknown_provider_status_is_separate_never_active_or_exposed() -> None:
    result = summarize_provider_rows(
        [
            {"vps_id": 1, "vps_status": "active", "repeat_invoices_cost": "3.00"},
            {"vps_id": 2, "vps_status": "unpublished-private-state", "repeat_invoices_cost": "7.00"},
        ]
    )
    assert result["total_vps"] == 2
    assert result["by_status"] == {"active": 1, "unknown": 1}
    assert result["unknown_status_count"] == 1
    assert result["status_mapping_complete"] is False
    assert result["listed_recurring_cost_by_status"] == {"active": "3.00", "unknown": "7.00"}
    assert "unpublished-private-state" not in repr(result)


def test_known_status_mapping_is_complete() -> None:
    result = summarize_provider_rows(
        [{"vps_id": 10, "vps_status": "pending", "repeat_invoices_cost": "1.00"}]
    )
    assert result["unknown_status_count"] == 0
    assert result["status_mapping_complete"] is True
