from dataclasses import replace

import pytest

from cybercore.caser41_metrics import RunObservation, aggregate_run_metrics


def _run(
    run_id: str,
    status: str,
    duration: float | None = 20.0,
    retries: int | None = 0,
    polls: int | None = 2,
) -> RunObservation:
    return RunObservation(run_id, status, duration, retries, polls)


def test_counts_all_terminal_outcomes_without_suppressing_failures() -> None:
    report = aggregate_run_metrics(
        [
            _run("a", "VERIFIED", 20, 1, 3),
            _run("b", "FAILED", 30, 2, 5),
            _run("c", "BLOCKED", None, 0, 1),
            _run("d", "ROLLED_BACK", None, 0, 1),
        ]
    )
    assert (report.total, report.verified, report.failed, report.blocked) == (4, 1, 1, 1)
    assert report.rolled_back == 1
    assert report.mean_time_to_verified_seconds == 20
    assert report.ci_retries_total == 3
    assert report.provider_poll_calls_total == 10


def test_unknown_telemetry_remains_unknown() -> None:
    report = aggregate_run_metrics([_run("a", "VERIFIED", None, None, None), _run("b", "FAILED")])
    assert report.mean_time_to_verified_seconds is None
    assert report.ci_retries_total is None
    assert report.provider_poll_calls_total is None


def test_empty_sample_is_not_a_success_rate() -> None:
    report = aggregate_run_metrics([])
    assert report.total == 0
    assert report.mean_time_to_verified_seconds is None


@pytest.mark.parametrize(
    "invalid",
    [
        _run("x", "UNKNOWN"),
        _run("x", "FAILED", -1),
        _run("x", "FAILED", float("nan")),
        _run("x", "FAILED", float("inf")),
        _run("x", "FAILED", 1, -1),
        _run("x", "FAILED", 1, True),
        _run("x", "FAILED", 1, 0, -2),
        replace(_run("x", "FAILED"), run_id=None),
        replace(_run("x", "FAILED"), status=None),
    ],
)
def test_invalid_observations_rejected(invalid: RunObservation) -> None:
    with pytest.raises(ValueError):
        aggregate_run_metrics([invalid])


def test_duplicate_run_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="DUPLICATE_RUN_ID"):
        aggregate_run_metrics([_run("same", "VERIFIED"), _run("same", "FAILED")])
