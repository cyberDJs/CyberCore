"""Safe, read-only VPS inventory normalization.

This module accepts a provider response; it never accesses credentials or
performs network operations. Provider transport must be reviewed separately.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


class InventoryFormatError(ValueError):
    """Provider response does not match an approved inventory schema."""


_ALLOWED_STATUS = frozenset({"active", "running", "stopped", "suspended", "pending", "cancelled", "terminated", "unknown"})


def summarize_vps_inventory(payload: object) -> dict[str, object]:
    """Reduce a provider inventory to a minimal, non-secret aggregate.

    Accepts either a list of service objects or a mapping with the exact
    `services` key. Never prints IPs, hostnames, credentials, customer IDs,
    invoice data, URLs or provider error bodies. Rejects ambiguous schemas.
    """
    if isinstance(payload, Mapping):
        if set(payload) != {"services"}:
            raise InventoryFormatError("unexpected inventory envelope")
        services = payload["services"]
    else:
        services = payload

    if not isinstance(services, Sequence) or isinstance(services, (str, bytes, bytearray)):
        raise InventoryFormatError("services must be a list")
    if len(services) > 10000:
        raise InventoryFormatError("inventory too large")

    statuses: Counter[str] = Counter()
    for service in services:
        if not isinstance(service, Mapping):
            raise InventoryFormatError("service must be an object")
        status = service.get("status")
        if not isinstance(status, str):
            raise InventoryFormatError("service status missing")
        normalized = status.strip().lower()
        if normalized not in _ALLOWED_STATUS:
            raise InventoryFormatError("unrecognized service status")
        statuses[normalized] += 1

    return {
        "source": "interserver",
        "verified_provider_response": False,
        "total_vps": len(services),
        "by_status": {key: statuses[key] for key in sorted(statuses)},
    }
