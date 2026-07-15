"""Minimal InterServer API client for safe read-only checks."""

from __future__ import annotations

from typing import Any

import httpx


class InterServerApiError(RuntimeError):
    """Raised when the InterServer API returns an unusable response."""


class InterServerClient:
    """Small typed wrapper around the InterServer API.

    The v0.1 client intentionally supports read-only operations only.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) ->