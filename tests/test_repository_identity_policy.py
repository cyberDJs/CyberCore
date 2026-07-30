from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from cybercore.entrypoint import main
from cybercore.repository_identity_policy import (
    RepositoryIdentityPolicyError,
    evaluate_repository_identity_policy,
    expected_repository_identity,
)


CANONICAL = "git:github.com/cyberDJs/CyberCore"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path, origin: str | None, expected: str = CANONICAL) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / ".cybercore").mkdir()
    (repo / ".cybercore" / "project.yaml").write_text(
        f"version: 1\n\nidentity:\n  name: CyberCore\n  repository: {expected}\n",
        encoding="utf-8",
    )
    if origin is not None:
        _git(repo, "remote", "add", "origin", origin)
    return repo


def test_expected_identity_is_read_from_project_kernel(tmp_path: Path) -> None:
    repo = _repo(tmp_path, None)

    assert expected_repository_identity(repo) == CANONICAL


def test_policy_verifies_matching_remote(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "git@github.com:cyberDJs/CyberCore.git")

    result = evaluate_repository_identity_policy(repo)

    assert result.status == "verified"
    assert result.compliant is True
    assert result.expected_identity == CANONICAL
    assert result.actual_identity == CANONICAL
    assert result.source == "remote"


def test_policy_rejects_unexpected_fork(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "https://github.com/attacker/CyberCore.git")

    result = evaluate_repository_identity_policy(repo)

    assert result.status == "failed"
    assert result.compliant is False
    assert result.actual_identity == "git:github.com/attacker/CyberCore"
    assert "unexpected repository or fork" in result.message


def test_policy_rejects_path_fallback(tmp_path: Path) -> None:
    repo = _repo(tmp_path, None)

    result = evaluate_repository_identity_policy(repo)

    assert result.status == "failed"
    assert result.compliant is False
    assert result.source == "path_fallback"
    assert "path fallback" in result.message


def test_advisory_policy_reports_warning(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "https://github.com/other/CyberCore.git")

    result = evaluate_repository_identity_policy(repo, advisory=True)

    assert result.status == "warning"
    assert result.compliant is False


def test_missing_canonical_identity_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / ".cybercore").mkdir()
    (repo / ".cybercore" / "project.yaml").write_text(
        "version: 1\nidentity:\n  name: CyberCore\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIdentityPolicyError, match="identity.repository"):
        expected_repository_identity(repo)


def test_identity_verify_cli_json_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path, "https://github.com/cyberDJs/CyberCore.git")

    exit_code = main(["--repo", str(repo), "--json", "identity", "verify"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "verified"
    assert payload["compliant"] is True


def test_identity_verify_cli_failure_and_advisory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path, "https://github.com/fork/CyberCore.git")

    failed = main(["--repo", str(repo), "identity", "verify"])
    failed_output = capsys.readouterr().out
    advisory = main(["--repo", str(repo), "identity", "verify", "--advisory"])
    advisory_output = capsys.readouterr().out

    assert failed == 1
    assert "Status: failed" in failed_output
    assert advisory == 0
    assert "Status: warning" in advisory_output
