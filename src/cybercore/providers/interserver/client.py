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
    ) -> None:
        if not api_key.strip():
            raise ValueError("InterServer API key must not be empty")

        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "X-API-KEY": api_key,
                "Accept": "application/json",
                "User-Agent": "CyberCore/0.1",
            },
            timeout=timeout_seconds,