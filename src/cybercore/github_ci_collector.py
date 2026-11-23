"""Authenticated, read-only GitHub Actions evidence acquisition (WB-165-02).

Acquisition does not attest CI PASS or authorize release. The upstream structural
reconciler still produces UNKNOWN for consistent, non-attested observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from http.client import HTTPSConnection
import json
import re
import ssl
from typing import Any
from urllib.parse import urlencode

from cybercore.caser41_github_snapshot import Job, Workflow

_REPO = "cyberDJs/CyberCore"
_API = "/repos/" + _REPO
_SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
_ALLOWED = frozenset({"CI", "CodeQL", "Action Kernel real CyberHIVE contract"})
_MAX_RUNS = 20
_MAX_JOBS = 100
_PAGE_SIZE = 25


class EvidenceAcquisitionError(ValueError):
    """Fail closed; exception messages never include response bodies or secrets."""


@dataclass(frozen=True)
class AcquiredCI:
    pr_number: int
    head_sha: str
    workflows: tuple[Workflow, ...]
    jobs: tuple[Job, ...]
    # Authenticated acquisition does not itself prove job provenance or PASS.
    status: str = "UNKNOWN"


class GitHubHTTPSReader:
    """Use only api.github.com:443 with an explicitly supplied GitHub token.

    No redirects, writes, arbitrary URLs, token persistence, or untrusted hosts.
    """

    def __init__(self, token: str) -> None:
        if type(token) is not str or not token or "\r" in token or "\n" in token:
            raise EvidenceAcquisitionError("INVALID_AUTH")
        self._token = token

    def get(self, path: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
        if not path.startswith(_API + "/") or "?" in path or "#" in path or ".." in path:
            raise EvidenceAcquisitionError("INVALID_ENDPOINT")
        target = path + ("?" + urlencode(params) if params else "")
        conn = HTTPSConnection("api.github.com", timeout=15, context=ssl.create_default_context())
        try:
            conn.request(
                "GET",
                target,
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "CyberCore-WB-165-02",
                },
            )
            response = conn.getresponse()
            if response.status != 200:
                raise EvidenceAcquisitionError("GITHUB_HTTP_ERROR")
            if int(response.getheader("Content-Length") or 0) > 2_000_000:
                raise EvidenceAcquisitionError("RESPONSE_TOO_LARGE")
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise EvidenceAcquisitionError("RESPONSE_TOO_LARGE")
            result = json.loads(body)
            if type(result) is not dict:
                raise EvidenceAcquisitionError("INVALID_RESPONSE")
            return result
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, EvidenceAcquisitionError):
                raise
            raise EvidenceAcquisitionError("GITHUB_READ_FAILED") from None
        finally:
            conn.close()


def _obj(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise EvidenceAcquisitionError("INVALID_RESPONSE")
    return value


def _positive(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise EvidenceAcquisitionError("INVALID_ID")
    return value


def _head(pr: dict[str, Any], number: int) -> str:
    if pr.get("number") != number or type(pr.get("number")) is not int:
        raise EvidenceAcquisitionError("PR_IDENTITY_DRIFT")
    head = _obj(pr.get("head"))
    repository = _obj(head.get("repo"))
    if repository.get("full_name") != _REPO:
        raise EvidenceAcquisitionError("FOREIGN_PR_REPOSITORY")
    sha = head.get("sha")
    if type(sha) is not str or not _SHA.fullmatch(sha):
        raise EvidenceAcquisitionError("INVALID_HEAD")
    return sha


def _pages(
    reader: GitHubHTTPSReader,
    endpoint: str,
    key: str,
    *,
    params: dict[str, str | int],
    max_items: int,
) -> list[dict[str, Any]]:
    """Require exact total_count, bounded pagination, and complete item count."""
    output: list[dict[str, Any]] = []
    expected_total: int | None = None
    for page in range(1, (max_items + _PAGE_SIZE - 1) // _PAGE_SIZE + 1):
        data = _obj(reader.get(endpoint, {**params, "per_page": _PAGE_SIZE, "page": page}))
        total = data.get("total_count")
        items = data.get(key)
        if type(total) is not int or total < 0 or total > max_items or type(items) is not list:
            raise EvidenceAcquisitionError("INCOMPLETE_PAGINATION")
        if expected_total is None:
            expected_total = total
        if total != expected_total:
            raise EvidenceAcquisitionError("PAGINATION_DRIFT")
        if len(items) > _PAGE_SIZE or len(output) + len(items) > total:
            raise EvidenceAcquisitionError("INCOMPLETE_PAGINATION")
        output.extend(_obj(item) for item in items)
        if len(output) == total:
            return output
        if len(items) != _PAGE_SIZE:
            raise EvidenceAcquisitionError("INCOMPLETE_PAGINATION")
    raise EvidenceAcquisitionError("INCOMPLETE_PAGINATION")


def collect_pr_ci(
    reader: GitHubHTTPSReader,
    *,
    pr_number: int,
    expected_sha: str,
) -> AcquiredCI:
    """Acquire full PR-associated runs and latest-attempt jobs, without side effects.

    Caller must supply a trusted reader with authenticated GitHub API access.
    Hard bounds intentionally reject larger collections pending redesign.
    """
    if type(pr_number) is not int or not 1 <= pr_number <= 1_000_000_000:
        raise EvidenceAcquisitionError("INVALID_PR_NUMBER")
    if type(expected_sha) is not str or _SHA.fullmatch(expected_sha) is None:
        raise EvidenceAcquisitionError("INVALID_SHA")
    pr_url = f"{_API}/pulls/{pr_number}"
    if _head(_obj(reader.get(pr_url)), pr_number) != expected_sha:
        raise EvidenceAcquisitionError("HEAD_DRIFT")

    runs = _pages(
        reader,
        f"{_API}/actions/runs",
        "workflow_runs",
        params={"head_sha": expected_sha, "event": "pull_request"},
        max_items=_MAX_RUNS,
    )
    workflows: list[Workflow] = []
    jobs: list[Job] = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for run in runs:
        run_id = _positive(run.get("id"))
        if run_id in seen_ids:
            raise EvidenceAcquisitionError("DUPLICATE_RUN")
        seen_ids.add(run_id)
        if run.get("event") != "pull_request" or run.get("head_sha") != expected_sha:
            raise EvidenceAcquisitionError("FOREIGN_RUN")
        repo = _obj(run.get("repository"))
        if repo.get("full_name") != _REPO:
            raise EvidenceAcquisitionError("FOREIGN_REPOSITORY")
        linked = run.get("pull_requests")
        if type(linked) is not list or not any(
            type(item) is dict and type(item.get("number")) is int and item["number"] == pr_number
            for item in linked
        ):
            raise EvidenceAcquisitionError("FOREIGN_PR_RUN")
        name = run.get("name")
        if type(name) is not str:
            raise EvidenceAcquisitionError("INVALID_WORKFLOW")
        if name not in _ALLOWED:
            continue
        if name in seen_names:
            raise EvidenceAcquisitionError("DUPLICATE_WORKFLOW")
        seen_names.add(name)
        _positive(run.get("run_attempt"))
        workflows.append(Workflow(run_id, name, run.get("status"), run.get("conclusion")))
        entries = _pages(
            reader,
            f"{_API}/actions/runs/{run_id}/jobs",
            "jobs",
            params={"filter": "latest"},
            max_items=_MAX_JOBS,
        )
        for entry in entries:
            if _positive(entry.get("run_id")) != run_id:
                raise EvidenceAcquisitionError("FOREIGN_RUN_JOB")
            jobs.append(
                Job(
                    run_id,
                    _positive(entry.get("id")),
                    entry.get("name"),
                    entry.get("status"),
                    entry.get("conclusion"),
                )
            )
            if len(jobs) > _MAX_JOBS:
                raise EvidenceAcquisitionError("TOO_MANY_JOBS")
    if seen_names != _ALLOWED:
        raise EvidenceAcquisitionError("MISSING_WORKFLOW")
    if _head(_obj(reader.get(pr_url)), pr_number) != expected_sha:
        raise EvidenceAcquisitionError("HEAD_DRIFT")
    return AcquiredCI(pr_number, expected_sha, tuple(workflows), tuple(jobs))
