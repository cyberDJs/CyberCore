"""Pure CASER run metrics, requiring complete typed outcome observations.

Metrics are descriptive; they never grant action authority, suppress failures,
or convert missing telemetry into successes.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


STATUSES = frozenset({"VERIFIED", "BLOCKED", "FAILED", "ROLLED_BACK"})


@dataclass(frozen=True)
class RunObservation:
    run_id: str
    status: str
    duration_seconds: float | None
    ci_retry_count: int | None
    provider_poll_calls: int | None


@dataclass(frozen=True)
class RunMetrics:
    total: int
    verified: int
    blocked: int
    failed: int
    rolled_back: int
    mean_time_to_verified_seconds: float | None
    ci_retries_total: int | None
    provider_poll_calls_total: int | None


def aggregate_run_metrics(observations: Iterable[RunObservation]) -> RunMetrics:
    """Reject partial records and duplicate runs, instead of guessing values."""
    entries = tuple(observations)
    ids: set[str] = set()
    for item in entries:
        if not isinstance(item, RunObservation):
            raise ValueError("INVALID_OBSERVATION")
        if not isinstance(item.run_id, str) or not item.run_id.strip():
            raise ValueError("INVALID_RUN_ID")
        if item.run_id in ids:
            raise ValueError("DUPLICATE_RUN_ID")
        ids.add(item.run_id)
        if not isinstance(item.status, str) or item.status not in STATUSES:
            raise ValueError("UNKNOWN_OUTCOME")
        if item.duration_seconds is not None:
            if isinstance(item.duration_seconds, bool) or not isinstance(
                item.duration_seconds, (float, int)
            ):
                raise ValueError("INVALID_DURATION")
            try:
                duration = float(item.duration_seconds)
            except (OverflowError, ValueError):
                raise ValueError("INVALID_DURATION") from None
            if not isfinite(duration) or duration < 0:
                raise ValueError("INVALID_DURATION")
        for count in (item.ci_retry_count, item.provider_poll_calls):
            if count is not None and (
                isinstance(count, bool) or not isinstance(count, int) or count < 0
            ):
                raise ValueError("INVALID_COUNT")

    verified = [item for item in entries if item.status == "VERIFIED"]
    mean_time: float | None = None
    if verified and all(item.duration_seconds is not None for item in verified):
        running_mean = 0.0
        for index, item in enumerate(verified, start=1):
            if item.duration_seconds is None:
                raise ValueError("INVALID_DURATION")
            duration = float(item.duration_seconds)
            running_mean += (duration - running_mean) / index
        mean_time = running_mean
    ci_retries = (
        sum(item.ci_retry_count for item in entries if item.ci_retry_count is not None)
        if entries and all(item.ci_retry_count is not None for item in entries)
        else None
    )
    poll_calls = (
        sum(item.provider_poll_calls for item in entries if item.provider_poll_calls is not None)
        if entries and all(item.provider_poll_calls is not None for item in entries)
        else None
    )
    return RunMetrics(
        total=len(entries),
        verified=len(verified),
        blocked=sum(item.status == "BLOCKED" for item in entries),
        failed=sum(item.status == "FAILED" for item in entries),
        rolled_back=sum(item.status == "ROLLED_BACK" for item in entries),
        mean_time_to_verified_seconds=mean_time,
        ci_retries_total=ci_retries,
        provider_poll_calls_total=poll_calls,
    )
