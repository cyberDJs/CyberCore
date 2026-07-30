from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import collect_checkpoint
from cybercore.commands.evidence import run_evidence_command
from cybercore.post_merge import plan_post_merge_transition
from cybercore.repository_identity_policy import RepositoryIdentityPolicyError


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path, *, configured: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "CyberCore Tests")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "remote", "add", "origin", "https://github.com/example/fork.git")
    (repo / ".cybercore").mkdir()
    identity = (
        "identity:\n  repository: git:github.com/cyberDJs/CyberCore\n"
        if configured
        else "identity:\n  name: Test\n"
    )
    (repo / ".cybercore" / "project.yaml").write_text(
        f"version: 1\n{identity}",
        encoding="utf-8",
    )
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "test fixture")
    return repo


def test_checkpoint_rejects_configured_identity_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(RepositoryIdentityPolicyError, match="Checkpoint collection rejected"):
        collect_checkpoint(repo)


def test_evidence_rejects_identity_before_command_execution(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    marker = repo / "should-not-exist"

    with pytest.raises(
        RepositoryIdentityPolicyError,
        match="Verification evidence generation rejected",
    ):
        run_evidence_command(
            repo,
            ["python", "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
            summary="not run",
            output=repo / "evidence.json",
        )

    assert not marker.exists()


def test_post_merge_rejects_identity_before_network_access(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    network_called = False

    def opener(*_args, **_kwargs):
        nonlocal network_called
        network_called = True
        raise AssertionError("network should not be called")

    with pytest.raises(RepositoryIdentityPolicyError, match="Post-merge transition rejected"):
        plan_post_merge_transition(repo, 1, opener=opener)

    assert network_called is False


def test_unconfigured_legacy_project_remains_backward_compatible(tmp_path: Path) -> None:
    repo = _repo(tmp_path, configured=False)

    checkpoint = collect_checkpoint(repo)

    assert checkpoint.commit
