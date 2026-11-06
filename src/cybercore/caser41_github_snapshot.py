"""Read-only reconciliation of GitHub Actions workflow/job snapshots.

Tool-returned lists need authenticated acquisition, head binding, and complete
pagination by the caller. A consistent snapshot is NOT an attestation.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from cybercore.caser41_ci_evidence import CheckObservation, evaluate_ci_evidence

_REQUIRED = {
    "CI": frozenset(
        {
            "quality",
            "package",
            "tests (python 3.11)",
            "tests (python 3.12)",
            "tests (python 3.13)",
            "tests (python 3.14)",
        }
    ),
    "CodeQL": frozenset({"codeql"}),
    "Action Kernel real CyberHIVE contract": frozenset({"real-hive-contract"}),
}
_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)


@dataclass(frozen=True)
class Workflow:
    run_id: int
    name: str
    status: str
    conclusion: str | None


@dataclass(frozen=True)
class Job:
    run_id: int
    job_id: int
    name: str
    status: str
    conclusion: str | None


@dataclass(frozen=True)
class Reconciliation:
    status: str
    reason: str


def reconcile_github_snapshot(
    *,
    expected_sha: str,
    provider_head_sha: str,
    workflows: object,
    jobs: object,
) -> Reconciliation:
    """Return only structural consistency, never authentication or merge approval."""
    if (
        type(expected_sha) is not str
        or _SHA.fullmatch(expected_sha) is None
        or type(provider_head_sha) is not str
        or _SHA.fullmatch(provider_head_sha) is None
    ):
        return Reconciliation("BLOCKED", "INVALID_SHA")
    if expected_sha != provider_head_sha:
        return Reconciliation("BLOCKED", "HEAD_DRIFT")
    if type(workflows) is not tuple or type(jobs) is not tuple:
        return Reconciliation("BLOCKED", "INVALID_COLLECTION")
    if not 1 <= len(workflows) <= 20 or not 1 <= len(jobs) <= 100:
        return Reconciliation("BLOCKED", "INVALID_COLLECTION")

    seen_workflows: dict[str, int] = {}
    all_run_ids: set[int] = set()
    for run in workflows:
        if type(run) is not Workflow:
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW")
        try:
            identity = (run.run_id, run.name, run.status, run.conclusion)
        except AttributeError:
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW")
        run_id, name, status, conclusion = identity
        if (
            type(run_id) is not int
            or run_id <= 0
            or type(name) is not str
            or type(status) is not str
            or (conclusion is not None and type(conclusion) is not str)
        ):
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW")
        if run_id in all_run_ids:
            return Reconciliation("BLOCKED", "DUPLICATE_RUN_ID")
        all_run_ids.add(run_id)
        # Validate every provider record, including unrelated workflows, before
        # ignoring its identity. A foreign run must not hide impossible states.
        if status not in {"requested", "waiting", "pending", "queued", "in_progress", "completed"}:
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW_STATE")
        if (status == "completed") != (conclusion is not None):
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW_STATE")
        if conclusion is not None and conclusion not in {
            "success",
            "failure",
            "cancelled",
            "skipped",
            "timed_out",
            "action_required",
            "neutral",
            "startup_failure",
            "stale",
        }:
            return Reconciliation("BLOCKED", "INVALID_WORKFLOW_STATE")
        if name not in _REQUIRED:
            continue
        if name in seen_workflows:
            return Reconciliation("BLOCKED", "DUPLICATE_WORKFLOW")
        seen_workflows[name] = run_id
        if status != "completed" or conclusion != "success":
            return Reconciliation("BLOCKED", "WORKFLOW_NOT_SUCCESSFUL")
    if seen_workflows.keys() != _REQUIRED.keys():
        return Reconciliation("BLOCKED", "MISSING_WORKFLOW")

    seen_job_ids: set[int] = set()
    seen_pairs: set[tuple[int, str]] = set()
    observations: list[CheckObservation] = []
    expected_job_ids = set(seen_workflows.values())
    if len(expected_job_ids) != len(seen_workflows):
        return Reconciliation("BLOCKED", "REUSED_WORKFLOW_ID")
    for job in jobs:
        if type(job) is not Job:
            return Reconciliation("BLOCKED", "INVALID_JOB")
        try:
            run_id, job_id, name, status, conclusion = (
                job.run_id,
                job.job_id,
                job.name,
                job.status,
                job.conclusion,
            )
        except AttributeError:
            return Reconciliation("BLOCKED", "INVALID_JOB")
        if (
            type(run_id) is not int
            or type(job_id) is not int
            or job_id <= 0
            or type(name) is not str
            or type(status) is not str
            or (conclusion is not None and type(conclusion) is not str)
        ):
            return Reconciliation("BLOCKED", "INVALID_JOB")
        # Even optional jobs must have coherent provider states before being
        # skipped. Invalid optional observations cannot certify consistency.
        if status not in {"requested", "waiting", "pending", "queued", "in_progress", "completed"}:
            return Reconciliation("BLOCKED", "INVALID_JOB_STATE")
        if (status == "completed") != (conclusion is not None):
            return Reconciliation("BLOCKED", "INVALID_JOB_STATE")
        if conclusion is not None and conclusion not in {
            "success",
            "failure",
            "cancelled",
            "skipped",
            "timed_out",
            "action_required",
            "neutral",
            "startup_failure",
            "stale",
        }:
            return Reconciliation("BLOCKED", "INVALID_JOB_STATE")
        if job_id in seen_job_ids or (run_id, name) in seen_pairs:
            return Reconciliation("BLOCKED", "DUPLICATE_JOB")
        seen_job_ids.add(job_id)
        seen_pairs.add((run_id, name))
        if run_id not in expected_job_ids:
            return Reconciliation("BLOCKED", "FOREIGN_RUN_JOB")
        workflow_name = next(key for key, value in seen_workflows.items() if value == run_id)
        if name not in _REQUIRED[workflow_name]:
            continue
        if status != "completed" or conclusion != "success":
            return Reconciliation("BLOCKED", "JOB_NOT_SUCCESSFUL")
        if workflow_name != "Action Kernel real CyberHIVE contract":
            observations.append(CheckObservation(name, expected_sha, status, conclusion))
    expected_pairs = {
        (seen_workflows[workflow_name], name)
        for workflow_name, required in _REQUIRED.items()
        for name in required
    }
    if not expected_pairs.issubset(seen_pairs):
        return Reconciliation("BLOCKED", "MISSING_JOB")
    verdict = evaluate_ci_evidence(expected_sha, observations)
    if not verdict.passed:
        return Reconciliation("BLOCKED", verdict.reason)
    return Reconciliation("CONSISTENT_ONLY", "PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED")
