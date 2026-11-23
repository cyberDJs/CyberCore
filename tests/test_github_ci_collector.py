from __future__ import annotations

from copy import deepcopy

import pytest

from cybercore.caser41_github_snapshot import reconcile_github_snapshot
from cybercore.github_ci_collector import (
    EvidenceAcquisitionError,
    GitHubHTTPSReader,
    collect_pr_ci,
)

SHA = "a" * 40
PREFIX = "/repos/cyberDJs/CyberCore"
RUN_NAMES = ("CI", "CodeQL", "Action Kernel real CyberHIVE contract")
JOB_NAMES = (
    ("quality", "package", "tests (python 3.11)", "tests (python 3.12)",
     "tests (python 3.13)", "tests (python 3.14)"),
    ("codeql",),
    ("real-hive-contract",),
)


class FakeReader(GitHubHTTPSReader):
    def __init__(self) -> None:
        self.pr = {"number": 165, "head": {"sha": SHA, "repo": {"full_name": "cyberDJs/CyberCore"}}}
        self.calls = []
        self.run_data = []
        self.job_data = {}
        for i, name in enumerate(RUN_NAMES, 1):
            run_id = 100 + i
            self.run_data.append({
                "id": run_id, "name": name, "event": "pull_request",
                "head_sha": SHA, "run_attempt": 1, "status": "completed",
                "conclusion": "success", "repository": {"full_name": "cyberDJs/CyberCore"},
                "pull_requests": [{"number": 165}],
            })
            self.job_data[run_id] = [
                {"run_id": run_id, "id": run_id * 100 + n, "name": item,
                 "status": "completed", "conclusion": "success"}
                for n, item in enumerate(JOB_NAMES[i - 1], 1)
            ]
        self.on_call = None

    def get(self, path, params=None):
        self.calls.append((path, params))
        if self.on_call is not None:
            self.on_call(path, params)
        if path == f"{PREFIX}/pulls/165":
            return deepcopy(self.pr)
        if path == f"{PREFIX}/actions/runs":
            items = self.run_data
            return {"total_count": len(items), "workflow_runs": deepcopy(
                items[(params["page"] - 1) * params["per_page"]:params["page"] * params["per_page"]]
            )}
        for run_id, jobs in self.job_data.items():
            if path == f"{PREFIX}/actions/runs/{run_id}/jobs":
                return {"total_count": len(jobs), "jobs": deepcopy(
                    jobs[(params["page"] - 1) * params["per_page"]:params["page"] * params["per_page"]]
                )}
        raise AssertionError(path)


def test_complete_authenticated_acquisition_remains_structural_unknown():
    reader = FakeReader()
    collected = collect_pr_ci(reader, pr_number=165, expected_sha=SHA)
    assert collected.status == "UNKNOWN"
    assert len(collected.workflows) == 3
    assert len(collected.jobs) == 8
    result = reconcile_github_snapshot(
        expected_sha=SHA, provider_head_sha=collected.head_sha,
        workflows=collected.workflows, jobs=collected.jobs,
    )
    assert result.status == "CONSISTENT_ONLY"
    assert len([x for x in reader.calls if x[0].endswith("/pulls/165")]) == 2


def test_head_changed_during_collection_is_rejected():
    reader = FakeReader()
    seen = 0
    def mutate(path, params):
        nonlocal seen
        if path.endswith("/pulls/165"):
            seen += 1
            if seen == 2:
                reader.pr["head"]["sha"] = "b" * 40
    reader.on_call = mutate
    with pytest.raises(EvidenceAcquisitionError, match="HEAD_DRIFT"):
        collect_pr_ci(reader, pr_number=165, expected_sha=SHA)


@pytest.mark.parametrize("tamper,error", [
    (lambda r: r.run_data[0].update(head_sha="b" * 40), "FOREIGN_RUN"),
    (lambda r: r.run_data[0].update(pull_requests=[{"number": 166}]), "FOREIGN_PR_RUN"),
    (lambda r: r.run_data[0].update(repository={"full_name": "other/repo"}), "FOREIGN_REPOSITORY"),
    (lambda r: r.run_data[0].update(run_attempt=0), "INVALID_ID"),
    (lambda r: r.run_data[1].update(name="CI"), "DUPLICATE_WORKFLOW"),
    (lambda r: r.run_data.pop(), "MISSING_WORKFLOW"),
    (lambda r: r.job_data[101][0].update(run_id=999), "FOREIGN_RUN_JOB"),
    (lambda r: r.pr["head"]["repo"].update(full_name="attacker/fork"), "FOREIGN_PR_REPOSITORY"),
])
def test_foreign_or_invalid_evidence_fail_closed(tamper, error):
    reader = FakeReader()
    tamper(reader)
    with pytest.raises(EvidenceAcquisitionError, match=error):
        collect_pr_ci(reader, pr_number=165, expected_sha=SHA)


def test_failed_job_is_not_promoted():
    reader = FakeReader()
    reader.job_data[101][0]["conclusion"] = "failure"
    data = collect_pr_ci(reader, pr_number=165, expected_sha=SHA)
    result = reconcile_github_snapshot(
        expected_sha=SHA, provider_head_sha=data.head_sha,
        workflows=data.workflows, jobs=data.jobs,
    )
    assert result.status == "BLOCKED"


def test_incomplete_pagination_rejected_even_when_all_mandatory_jobs_present():
    reader = FakeReader()
    orig = reader.get
    def broken(path, params=None):
        response = orig(path, params)
        if path.endswith("/actions/runs"):
            response["total_count"] = 4
        return response
    reader.get = broken
    with pytest.raises(EvidenceAcquisitionError, match="INCOMPLETE_PAGINATION"):
        collect_pr_ci(reader, pr_number=165, expected_sha=SHA)


def test_over_limit_collection_rejected():
    reader = FakeReader()
    reader.run_data = reader.run_data * 8
    with pytest.raises(EvidenceAcquisitionError, match="INCOMPLETE_PAGINATION"):
        collect_pr_ci(reader, pr_number=165, expected_sha=SHA)


def test_reader_rejects_malformed_token_and_untrusted_endpoint():
    with pytest.raises(EvidenceAcquisitionError, match="INVALID_AUTH"):
        GitHubHTTPSReader("secret\nBearer attack")
    safe = GitHubHTTPSReader("placeholder-for-test")
    with pytest.raises(EvidenceAcquisitionError, match="INVALID_ENDPOINT"):
        safe.get("/repos/other/repo/pulls/165")


def test_multi_page_jobs_are_exhaustively_collected():
    reader = FakeReader()
    for i in range(22):
        reader.job_data[101].append({
            "run_id": 101, "id": 11000 + i, "name": f"optional-{i}",
            "status": "completed", "conclusion": "success",
        })
    result = collect_pr_ci(reader, pr_number=165, expected_sha=SHA)
    assert len(result.jobs) == 30
    pages = [params["page"] for path, params in reader.calls if path.endswith("/101/jobs")]
    assert pages == [1, 2]


def test_pagination_total_count_changing_between_pages_fails_closed():
    reader = FakeReader()
    for i in range(20):
        reader.job_data[101].append({
            "run_id": 101, "id": 12000 + i, "name": f"optional-{i}",
            "status": "completed", "conclusion": "success",
        })
    original = reader.get
    def inconsistent(path, params=None):
        response = original(path, params)
        if path.endswith("/101/jobs") and params["page"] == 2:
            response["total_count"] += 1
        return response
    reader.get = inconsistent
    with pytest.raises(EvidenceAcquisitionError, match="PAGINATION_DRIFT"):
        collect_pr_ci(reader, pr_number=165, expected_sha=SHA)
