from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WatchdogDecision:
    action: str
    reason: str


def evaluate_watchdog(
    *,
    elapsed_seconds: float,
    maximum_wall_seconds: int,
    consecutive_failures: int,
    max_consecutive_failures: int,
    duplicate_count: int,
    max_duplicate_steps: int,
) -> WatchdogDecision:
    if elapsed_seconds >= maximum_wall_seconds:
        return WatchdogDecision("STOP", "maximum wall budget exhausted")
    if consecutive_failures >= max_consecutive_failures:
        return WatchdogDecision("REPLAN", "consecutive failure limit reached")
    if duplicate_count >= max_duplicate_steps:
        return WatchdogDecision("REPLAN", "duplicate-step limit reached")
    return WatchdogDecision("CONTINUE", "healthy")
