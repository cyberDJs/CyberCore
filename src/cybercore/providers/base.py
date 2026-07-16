"""Shared provider contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class HealthStatus(StrEnum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True, slots=True)
class HealthResult:
    provider: str
    status: HealthStatus
    message: str


class Provider(Protocol):
    """Minimal provider contract for the first implementation increment."""

    name: str

    def health(self) -> HealthResult:
        """Return provider connectivity and configuration health."""
