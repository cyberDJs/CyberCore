"""InterServer REST VPS list transport; no logging and no credential persistence.

Endpoint contract: InterServer Management API 0.9.0 GET /apiv2/vps,
X-API-KEY header, response array of VpsRow. Never invoke other GET routes:
some provider GET operations are state-changing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any


VPS_LIST_URL = "https://my.interserver.net/apiv2/vps"
MAX_RESPONSE_BYTES = 1024 * 1024
STATUSES = frozenset({"active", "pending", "suspended", "cancelled"})


class InterServerInventoryError(ValueError):
    """Safe error with no provider response text or secret values."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def summarize_provider_rows(payload: object) -> dict[str, object]:
    """Validate canonical InterServer VpsRow fields and return only aggregates."""
    if not isinstance(payload, list) or len(payload) > 10000:
        raise InterServerInventoryError("invalid VPS listing shape")
    statuses: Counter[str] = Counter()
    totals: dict[str, Decimal] = {}
    seen_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, Mapping):
            raise InterServerInventoryError("invalid VPS row")
        identifier = item.get("vps_id")
        if isinstance(identifier, bool) or not isinstance(identifier, (int, str)):
            raise InterServerInventoryError("invalid VPS identifier")
        identifier = str(identifier)
        if not identifier.isdecimal() or identifier in seen_ids:
            raise InterServerInventoryError("invalid or duplicate VPS identifier")
        seen_ids.add(identifier)
        status = item.get("vps_status")
        if not isinstance(status, str) or status not in STATUSES:
            raise InterServerInventoryError("unexpected VPS status")
        try:
            cost = Decimal(str(item["repeat_invoices_cost"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
            raise InterServerInventoryError("invalid recurring VPS cost") from None
        if not cost.is_finite() or cost < 0:
            raise InterServerInventoryError("invalid recurring VPS cost")
        statuses[status] += 1
        totals[status] = totals.get(status, Decimal("0")) + cost

    return {
        "source": "interserver",
        "total_vps": len(payload),
        "by_status": {s: statuses[s] for s in sorted(statuses)},
        "listed_recurring_cost_by_status": {
            s: format(totals[s], "f") for s in sorted(totals)
        },
        "cost_currency": "UNVERIFIED",
        "billing_verified": False,
    }


def fetch_vps_inventory(
    api_key: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> dict[str, object]:
    """Call only the allowlisted read endpoint, never return raw provider data.

    Default opener blocks redirects, preventing accidental credential forwarding.
    Injectable opener supports network-free unit tests.
    """
    if not api_key or not api_key.strip():
        raise InterServerInventoryError("API key unavailable")
    request = urllib.request.Request(
        VPS_LIST_URL,
        headers={"X-API-KEY": api_key, "Accept": "application/json"},
        method="GET",
    )
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open
    try:
        with opener(request, timeout=10) as response:
            if response.getcode() != 200:
                raise InterServerInventoryError("VPS inventory request failed")
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise InterServerInventoryError("VPS inventory request failed") from None
    if len(content) > MAX_RESPONSE_BYTES:
        raise InterServerInventoryError("VPS inventory response too large")
    try:
        parsed = json.loads(content)
    except (ValueError, UnicodeError):
        raise InterServerInventoryError("invalid VPS inventory JSON") from None
    return summarize_provider_rows(parsed)
