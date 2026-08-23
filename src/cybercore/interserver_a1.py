from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


CATALOG_URL = "https://my.interserver.net/apiv2/vps/order"
QUOTE_URL = CATALOG_URL
TARGET_HOSTNAME = "tasks.cyberdjs.org"
MAX_MONTHLY_USD = Decimal("3.00")
MIN_RAM_MIB = 2048
MIN_DISK_GIB = 30


class A1ProbeError(RuntimeError):
    """Fail-closed error for the WB-0035 A1 read-only provider probe."""


@dataclass(frozen=True)
class Candidate:
    platform: str
    slices: int
    os_distro: str
    os_version: str
    control_panel: str
    period_months: int
    location_id: int
    location_name: str
    currency: str
    catalog_price_month: Decimal
    ram_mib: int
    disk_gib: int
    transfer_gib: int
    public_hostname: str = TARGET_HOSTNAME

    def as_safe_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["catalog_price_month"] = f"{self.catalog_price_month:.2f}"
        return data


class _NoRedirectHandler(HTTPRedirectHandler):
    def http_error_302(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
    ) -> Any:
        raise A1ProbeError("provider response attempted an unexpected redirect")

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def _decimal(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise A1ProbeError(f"provider response has invalid numeric field: {label}")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise A1ProbeError(f"provider response has invalid numeric field: {label}") from exc
    if not number.is_finite():
        raise A1ProbeError(f"provider response has non-finite numeric field: {label}")
    return number


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise A1ProbeError(f"provider response has invalid integer field: {label}")
    try:
        number = int(str(value))
    except (TypeError, ValueError) as exc:
        raise A1ProbeError(f"provider response has invalid integer field: {label}") from exc
    if number <= 0:
        raise A1ProbeError(f"provider response has non-positive integer field: {label}")
    return number


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise A1ProbeError(f"provider response requires mapping field: {label}")
    return value


def _contains_scalar(value: object, expected: str) -> bool:
    if isinstance(value, dict):
        return any(
            key == expected or _contains_scalar(child, expected) for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_scalar(child, expected) for child in value)
    return isinstance(value, str) and value == expected


def select_candidate(catalog: dict[str, object]) -> Candidate:
    currency = catalog.get("currency")
    if currency != "USD":
        raise A1ProbeError("A1 requires USD account pricing for the USD 3.00 budget gate")

    platform_names = _mapping(catalog.get("platformNames"), "platformNames")
    if "kvm" not in platform_names:
        raise A1ProbeError("KVM is not present in the live VPS catalog")

    os_names = _mapping(catalog.get("osNames"), "osNames")
    if "ubuntu" not in os_names:
        raise A1ProbeError("Ubuntu is not present in the live VPS catalog")

    templates = _mapping(catalog.get("templates"), "templates")
    if not _contains_scalar(templates.get("kvm"), "ubuntu24"):
        raise A1ProbeError("Ubuntu 24 template is not present in the live KVM catalog")

    location_stock = _mapping(catalog.get("locationStock"), "locationStock")
    location_names = _mapping(catalog.get("locationNames"), "locationNames")
    candidates: list[tuple[int, str]] = []
    for raw_id, raw_stock in location_stock.items():
        stock = _mapping(raw_stock, f"locationStock.{raw_id}")
        if stock.get("kvm") is not True:
            continue
        try:
            location_id = int(raw_id)
        except ValueError:
            continue
        name = location_names.get(raw_id)
        candidates.append((location_id, name if isinstance(name, str) else f"location-{raw_id}"))

    if not candidates:
        raise A1ProbeError("no KVM location reports live stock")

    location_id, location_name = sorted(candidates)[0]
    monthly = _decimal(catalog.get("vpsNyCost"), "vpsNyCost")
    if monthly > MAX_MONTHLY_USD:
        raise A1ProbeError("live catalog price exceeds the authorized USD 3.00 monthly ceiling")

    ram_mib = _positive_int(catalog.get("ramSlice"), "ramSlice")
    disk_gib = _positive_int(catalog.get("hdSlice"), "hdSlice")
    transfer_gib = _positive_int(catalog.get("bwSlice"), "bwSlice")
    if ram_mib < MIN_RAM_MIB:
        raise A1ProbeError("live catalog RAM is below the WB-0035 minimum")
    if disk_gib < MIN_DISK_GIB:
        raise A1ProbeError("live catalog disk is below the WB-0035 minimum")

    return Candidate(
        platform="kvm",
        slices=1,
        os_distro="ubuntu",
        os_version="ubuntu24",
        control_panel="none",
        period_months=1,
        location_id=location_id,
        location_name=location_name,
        currency="USD",
        catalog_price_month=monthly,
        ram_mib=ram_mib,
        disk_gib=disk_gib,
        transfer_gib=transfer_gib,
    )


def build_quote_payload(candidate: Candidate) -> dict[str, object]:
    return {
        "osDistro": candidate.os_distro,
        "slices": candidate.slices,
        "vpsPlatform": candidate.platform,
        "controlpanel": candidate.control_panel,
        "period": candidate.period_months,
        "location": candidate.location_id,
        "osVersion": candidate.os_version,
        "hostname": candidate.public_hostname,
        "coupon": "",
        "rootpass": secrets.token_urlsafe(32),
        "comment": "WB-0035 A1 quote validation only; no order",
    }


def sanitize_quote(candidate: Candidate, response: dict[str, object]) -> dict[str, object]:
    if response.get("continue") is not True:
        raise A1ProbeError("provider quote validation did not return continue=true")

    errors = response.get("errors")
    if errors not in (None, []):
        raise A1ProbeError("provider quote validation returned one or more errors")

    expected_response = {
        "platform": candidate.platform,
        "os": candidate.os_distro,
        "version": candidate.os_version,
        "controlpanel": candidate.control_panel,
    }
    for key, expected in expected_response.items():
        if response.get(key) != expected:
            raise A1ProbeError(f"provider quote response mismatch for field: {key}")

    if str(response.get("slices")) != str(candidate.slices):
        raise A1ProbeError("provider quote response mismatch for slices")

    period = _positive_int(response.get("period"), "period")
    location = _positive_int(response.get("location"), "location")
    if period != candidate.period_months:
        raise A1ProbeError("provider quote response mismatch for period")
    if location != candidate.location_id:
        raise A1ProbeError("provider quote response mismatch for location")

    monthly = _decimal(
        response.get("monthly_service_cost", response.get("repeat_service_cost")),
        "monthly_service_cost",
    )
    service_cost = _decimal(response.get("service_cost"), "service_cost")
    if monthly > MAX_MONTHLY_USD:
        raise A1ProbeError("live quote exceeds the authorized USD 3.00 monthly ceiling")
    if service_cost < monthly:
        raise A1ProbeError("provider quote service_cost is unexpectedly below monthly cost")

    one_time = service_cost - monthly
    safe_fingerprint_source = {
        "platform": candidate.platform,
        "slices": candidate.slices,
        "os": candidate.os_distro,
        "version": candidate.os_version,
        "controlpanel": candidate.control_panel,
        "period": candidate.period_months,
        "location": candidate.location_id,
        "monthly": f"{monthly:.2f}",
        "service_cost": f"{service_cost:.2f}",
    }
    fingerprint = hashlib.sha256(
        json.dumps(safe_fingerprint_source, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]

    return {
        "version": 1,
        "work_block": "WB-0035",
        "provider": "InterServer",
        "evidence_mode": "LIVE_READ_ONLY",
        "response_sanitized": True,
        "secret_values_recorded": False,
        "provider_contact_performed": True,
        "order_performed": False,
        "payment_performed": False,
        "currency": "USD",
        "recurring_price_usd_month": f"{monthly:.2f}",
        "one_time_price_usd": f"{one_time:.2f}",
        "platform": candidate.platform,
        "slices": candidate.slices,
        "os_distro": candidate.os_distro,
        "os_version": candidate.os_version,
        "control_panel": candidate.control_panel,
        "period_months": candidate.period_months,
        "quantity": 1,
        "stock_available": True,
        "resources": {
            "ram_mib": candidate.ram_mib,
            "disk_gib": candidate.disk_gib,
        },
        "public_hostname": candidate.public_hostname,
        "quote_reference": f"wb0035-a1-{fingerprint}",
    }


def safe_catalog_receipt(candidate: Candidate) -> dict[str, object]:
    return {
        "version": 1,
        "work_block": "WB-0035",
        "phase": "A1",
        "provider": "InterServer",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "response_sanitized": True,
        "secret_values_recorded": False,
        "provider_contact_performed": True,
        "order_performed": False,
        "payment_performed": False,
        "candidate": candidate.as_safe_dict(),
    }


def _request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, object]:
    if url not in {CATALOG_URL, QUOTE_URL}:
        raise A1ProbeError("A1 probe refused an unapproved provider URL")
    if method not in {"GET", "PUT"}:
        raise A1ProbeError("A1 probe refused an unapproved HTTP method")
    if not api_key:
        raise A1ProbeError("InterServer credential alias is not available in runtime")

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "User-Agent": "CyberCore-WB0035-A1/1.0",
        "X-API-KEY": api_key,
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    opener = build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read(2_000_000)
    except HTTPError as exc:
        raise A1ProbeError(f"InterServer returned HTTP {exc.code}") from None
    except URLError as exc:
        raise A1ProbeError("InterServer connection failed before a safe response was obtained") from exc

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise A1ProbeError("InterServer returned a non-JSON or undecodable response") from exc
    if not isinstance(decoded, dict) or not all(isinstance(key, str) for key in decoded):
        raise A1ProbeError("InterServer returned an unexpected response shape")
    return decoded


def run_live_a1(api_key: str, out_dir: Path) -> tuple[Path, Path]:
    catalog = _request_json("GET", CATALOG_URL, api_key)
    candidate = select_candidate(catalog)

    quote_payload = build_quote_payload(candidate)
    quote_response = _request_json("PUT", QUOTE_URL, api_key, quote_payload)
    safe_quote = sanitize_quote(candidate, quote_response)
    safe_catalog = safe_catalog_receipt(candidate)

    out_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = out_dir / "interserver-vps-catalog.live.json"
    quote_path = out_dir / "interserver-vps-quote.live.json"
    catalog_path.write_text(
        json.dumps(safe_catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    quote_path.write_text(
        json.dumps(safe_quote, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return catalog_path, quote_path
