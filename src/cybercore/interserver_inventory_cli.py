"""Manually invoked InterServer read-only VPS inventory entry point.

This module emits only sanitized aggregate data; never logs credentials or raw
provider responses. Intended for a trusted, manually triggered GitHub workflow.
"""

from __future__ import annotations

import json
import os
import sys

from cybercore.interserver_provider import InterServerInventoryError, fetch_vps_inventory


def main() -> int:
    key = os.environ.get("INTERSERVER_API_KEY", "")
    if not key:
        print("InterServer inventory blocked: key not provisioned", file=sys.stderr)
        return 2
    try:
        result = fetch_vps_inventory(key)
    except InterServerInventoryError as exc:
        diagnostic = f"InterServer inventory blocked: {exc.category}"
        if exc.category == "http_error" and exc.http_status is not None:
            diagnostic += f" (HTTP {exc.http_status})"
        print(diagnostic, file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
