"""Provider contracts used by CyberCore."""

from __future__ import annotations

from typing import Any, Protocol


class Provider(Protocol):
    """Minimal provider interface for discovery and health operations."""

    name: str

    def inventory(self) -> dict[str, Any]:
        """Return a machine-readable provider inventory."""

    def health(self) -> dict[str, Any]:
        """Return a non-destructive provider health summary."""
