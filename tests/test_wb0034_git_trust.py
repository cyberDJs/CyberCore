from __future__ import annotations

from pathlib import Path
import subprocess

from cybercore.first_write_packet import _git_main_commit


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.name", "WB0034 Test")
    _run_git(repo, "config", "user.email", "wb0034@example.invalid")
    (repo / "source.txt").write_text("trusted main\n", encoding="utf-8")
    _run_git(repo, "add", "source.txt")
    _run_git(repo, "commit", "-m", "trusted main")
    return repo


def test_trusted_main_fails_closed_when_origin_main_ref_is_dangling(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    remote_ref = repo / ".git/refs/remotes/origin/main"
    remote_ref.parent.mkdir(parents=True)
    remote_ref.write_text("f" * 40 + "\n", encoding="ascii")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("origin/main" in error for error in errors)
