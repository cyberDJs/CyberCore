from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore import first_write_packet as packet_module
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


def _init_origin(tmp_path: Path, repo: Path) -> Path:
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _run_git(origin, "init", "--bare")
    _run_git(repo, "remote", "add", "origin", str(origin))
    _run_git(repo, "push", "-u", "origin", "main")
    return origin


def _configure_identity(
    repo: Path,
    identity: str = "git:github.com/cyberDJs/CyberCore",
) -> None:
    project = repo / ".cybercore/project.yaml"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(
        f"version: 1\nidentity:\n  repository: {identity}\n",
        encoding="utf-8",
    )


def _bypass_identity_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        packet_module,
        "enforce_configured_repository_identity_policy",
        lambda *_args, **_kwargs: None,
    )


def test_trusted_main_fails_closed_when_origin_main_ref_is_dangling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_identity_policy(monkeypatch)
    repo = _init_repo(tmp_path)
    remote_ref = repo / ".git/refs/remotes/origin/main"
    remote_ref.parent.mkdir(parents=True)
    remote_ref.write_text("f" * 40 + "\n", encoding="ascii")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("origin/main" in error for error in errors)


def test_trusted_main_refreshes_stale_origin_main_before_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_identity_policy(monkeypatch)
    repo = _init_repo(tmp_path)
    _init_origin(tmp_path, repo)
    old_commit = _run_git(repo, "rev-parse", "HEAD")

    (repo / "source.txt").write_text("new trusted main\n", encoding="utf-8")
    _run_git(repo, "add", "source.txt")
    _run_git(repo, "commit", "-m", "advance main")
    new_commit = _run_git(repo, "rev-parse", "HEAD")
    _run_git(repo, "push", "origin", "main")
    _run_git(repo, "update-ref", "refs/remotes/origin/main", old_commit)
    assert _run_git(repo, "rev-parse", "refs/remotes/origin/main") == old_commit

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit == new_commit
    assert not errors
    assert _run_git(repo, "rev-parse", "refs/remotes/origin/main") == new_commit


def test_trusted_main_blocks_when_origin_refresh_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bypass_identity_policy(monkeypatch)
    repo = _init_repo(tmp_path)
    _run_git(repo, "remote", "add", "origin", str(tmp_path / "missing-origin.git"))

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("refresh trusted origin/main" in error for error in errors)


def test_trusted_main_rejects_missing_pinned_canonical_identity(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _run_git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("requires pinned canonical repository identity" in error for error in errors)


def test_trusted_main_rejects_lossy_quoted_canonical_identity(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    project = repo / ".cybercore/project.yaml"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(
        "version: 1\nidentity:\n  repository: \"'git:github.com/cyberDJs/CyberCore'\"\n",
        encoding="utf-8",
    )
    _run_git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("normalized git: form" in error for error in errors)


def test_trusted_main_rejects_duplicate_identity_mapping(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    project = repo / ".cybercore/project.yaml"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(
        "version: 1\n"
        "identity:\n"
        "  repository: git:github.com/cyberDJs/CyberCore\n"
        "identity:\n"
        "  repository: git:github.com/attacker/CyberCore\n",
        encoding="utf-8",
    )
    _run_git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("duplicate mapping keys" in error for error in errors)


def test_trusted_main_rejects_duplicate_repository_key(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    project = repo / ".cybercore/project.yaml"
    project.parent.mkdir(parents=True, exist_ok=True)
    project.write_text(
        "version: 1\n"
        "identity:\n"
        "  repository: git:github.com/cyberDJs/CyberCore\n"
        "  repository: git:github.com/attacker/CyberCore\n",
        encoding="utf-8",
    )
    _run_git(repo, "remote", "add", "origin", "https://github.com/cyberDJs/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("duplicate mapping keys" in error for error in errors)


def test_trusted_main_rejects_changed_pinned_canonical_identity(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _configure_identity(repo, "git:github.com/attacker/CyberCore")
    _run_git(repo, "remote", "add", "origin", "https://github.com/attacker/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("requires pinned canonical repository identity" in error for error in errors)


def test_trusted_main_rejects_origin_that_violates_canonical_repository_identity(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_identity(repo)
    _run_git(repo, "remote", "add", "origin", "https://github.com/attacker/CyberCore.git")

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("repository identity policy rejected trusted main" in error for error in errors)


def test_trusted_main_rejects_path_fallback_when_canonical_identity_is_configured(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    _configure_identity(repo)

    errors: list[str] = []
    commit = _git_main_commit(repo, errors)

    assert commit is None
    assert any("repository identity policy rejected trusted main" in error for error in errors)
