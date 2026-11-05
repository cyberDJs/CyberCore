from dataclasses import replace

import pytest

from cybercore.caser41_github_snapshot import Job, Workflow, reconcile_github_snapshot

SHA = "a" * 40
RUNS = (
    Workflow(101, "CI", "completed", "success"),
    Workflow(102, "CodeQL", "completed", "success"),
    Workflow(103, "Action Kernel real CyberHIVE contract", "completed", "success"),
)
JOBS = (
    Job(101, 1, "quality", "completed", "success"),
    Job(101, 2, "package", "completed", "success"),
    Job(101, 3, "tests (python 3.11)", "completed", "success"),
    Job(101, 4, "tests (python 3.12)", "completed", "success"),
    Job(101, 5, "tests (python 3.13)", "completed", "success"),
    Job(101, 6, "tests (python 3.14)", "completed", "success"),
    Job(102, 7, "codeql", "completed", "success"),
    Job(103, 8, "real-hive-contract", "completed", "success"),
)


def _result(
    workflows: object = RUNS,
    jobs: object = JOBS,
    *,
    provider_head_sha: str = SHA,
) -> str:
    return reconcile_github_snapshot(
        expected_sha=SHA,
        provider_head_sha=provider_head_sha,
        workflows=workflows,
        jobs=jobs,
    ).reason


def test_real_provider_job_names_are_consistent_but_not_authenticated() -> None:
    result = reconcile_github_snapshot(
        expected_sha=SHA,
        provider_head_sha=SHA,
        workflows=RUNS,
        jobs=JOBS,
    )
    assert result.status == "CONSISTENT_ONLY"
    assert result.reason == "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED"


def test_stale_head_is_blocked() -> None:
    assert _result(provider_head_sha="b" * 40) == "HEAD_DRIFT"


def test_missing_codeql_or_real_cyberhive_job_is_blocked() -> None:
    assert _result(jobs=JOBS[:-2] + JOBS[-1:]) == "MISSING_JOB"
    assert _result(jobs=JOBS[:-1]) == "MISSING_JOB"


def test_successful_codeql_display_cannot_replace_lowercase_job() -> None:
    jobs = JOBS[:6] + (replace(JOBS[6], name="CodeQL"),) + JOBS[7:]
    assert _result(jobs=jobs) == "MISSING_JOB"


def test_partial_or_failed_required_job_never_passes() -> None:
    pending = JOBS[:2] + (replace(JOBS[2], status="in_progress", conclusion=None),) + JOBS[3:]
    assert _result(jobs=pending) == "JOB_NOT_SUCCESSFUL"
    failed = JOBS[:2] + (replace(JOBS[2], conclusion="failure"),) + JOBS[3:]
    assert _result(jobs=failed) == "JOB_NOT_SUCCESSFUL"


def test_failed_workflow_is_blocked_even_when_jobs_succeed() -> None:
    runs = (replace(RUNS[0], conclusion="failure"),) + RUNS[1:]
    assert _result(workflows=runs) == "WORKFLOW_NOT_SUCCESSFUL"


def test_replay_and_foreign_run_jobs_are_blocked() -> None:
    assert _result(jobs=JOBS + (JOBS[0],)) == "DUPLICATE_JOB"
    assert _result(jobs=JOBS[:1] + (replace(JOBS[1], run_id=99),) + JOBS[2:]) == ("FOREIGN_RUN_JOB")
    assert _result(workflows=RUNS + (RUNS[0],)) == "DUPLICATE_RUN_ID"


@pytest.mark.parametrize(
    "workflows,jobs,expected",
    [
        ((), JOBS, "INVALID_COLLECTION"),
        (RUNS[:-1], JOBS, "MISSING_WORKFLOW"),
        (RUNS, JOBS[:-1] + (replace(JOBS[-1], job_id=1),), "DUPLICATE_JOB"),
        (RUNS, JOBS[:-1] + (replace(JOBS[-1], job_id=True),), "INVALID_JOB"),
        (RUNS, JOBS[:-1] + (replace(JOBS[-1], name=None),), "INVALID_JOB"),
        (RUNS + (object(),), JOBS, "INVALID_WORKFLOW"),
        (RUNS, JOBS + (object(),), "INVALID_JOB"),
    ],
)
def test_bad_shapes_are_rejected(workflows: object, jobs: object, expected: str) -> None:
    assert _result(workflows=workflows, jobs=jobs) == expected


def test_incomplete_dataclass_is_blocked() -> None:
    broken = object.__new__(Workflow)
    assert _result(workflows=RUNS + (broken,)) == "INVALID_WORKFLOW"
    broken_job = object.__new__(Job)
    assert _result(jobs=JOBS + (broken_job,)) == "INVALID_JOB"


def test_foreign_workflow_reusing_required_run_id_is_blocked() -> None:
    forged = Workflow(101, "Foreign", "completed", "success")
    assert _result(workflows=RUNS + (forged,)) == "DUPLICATE_RUN_ID"


def test_unrelated_workflow_with_distinct_run_id_does_not_count_as_required() -> None:
    extra = Workflow(104, "Foreign", "completed", "success")
    assert _result(workflows=RUNS + (extra,)) == ("PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED")


@pytest.mark.parametrize(
    "status,conclusion",
    [
        ("in_progress", "success"),
        ("", None),
        ("completed", None),
        ("completed", ""),
        ("queued", "failure"),
        ("completed", "unknown"),
    ],
)
def test_foreign_workflow_invalid_state_fails_closed(
    status: str, conclusion: str | None,
) -> None:
    foreign = Workflow(104, "Foreign", status, conclusion)
    assert _result(workflows=RUNS + (foreign,)) == "INVALID_WORKFLOW_STATE"


def test_foreign_workflow_valid_pending_state_is_ignored() -> None:
    foreign = Workflow(104, "Foreign", "in_progress", None)
    assert _result(workflows=RUNS + (foreign,)) == (
        "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED"
    )
