"""CyberCore configuration loading.

Secrets are read from environment variables only. They must never be committed.
"""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings shared by CyberCore providers."""

    interserver_api_key: str | None = None
    interserver_base_url: str = "https://my.interserver.net/apiv2"

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from process environment variables."""

        return cls(
            interserver_api_key=os.getenv("INTERSERVER_API_KEY"),
            interserver_base_url=os.getenv(
                "INTERSERVER_API_BASE_URL",
                "https://my.interserver.net/apiv2",
            ).rstrip("/"),
        )

    def require_interserver_api_key(self) -> str:
        """Return the InterServer API key or raise a safe configuration error."""

        if not self.interserver_api_key:
            raise RuntimeError(
                "INTERSERVER_API_KEY is not configured. Store it outside Git and export it "
                "before running InterServer commands."
            )
        return self.interserver_api_key
