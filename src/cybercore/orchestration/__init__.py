"""Optional orchestration workflows for CyberCore."""

from __future__ import annotations

from typing import Any

__all__ = [
    "bind_provider_observations",
    "build_sot_reconciler",
    "build_trusted_sot_reconciler",
]


def __getattr__(name: str) -> Any:
    if name == "bind_provider_observations":
        from cybercore.orchestration.source_binding import bind_provider_observations

        return bind_provider_observations
    if name == "build_sot_reconciler":
        from cybercore.orchestration.sot import build_sot_reconciler

        return build_sot_reconciler
    if name == "build_trusted_sot_reconciler":
        from cybercore.orchestration.trusted_sot import build_trusted_sot_reconciler

        return build_trusted_sot_reconciler
    raise AttributeError(name)
