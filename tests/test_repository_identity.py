from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore.repository_identity import (
    RepositoryIdentityError,
    normalize_git_remote,
    repository_identity,
)


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        ("https://github.com/cyberDJs/CyberCore.git", "git:github.com/cyberDJs/CyberCore"),
        ("http://github.com:80/cyberDJs/CyberCore/", "git:github.com/cyberDJs/CyberCore"),
        ("ssh://git@GitHub.com:22/cyberDJs/CyberCore.git", "git:github.com/cyberDJs/CyberCore"),
        ("git@github.com:cyberDJs/CyberCore.git", "git:github.com/cyberDJs/CyberCore"),
        ("git://example.test:9418/team/project.git", "git:example.test/team/project"),
    ],
)
def test_normalize_git_remote(remote: str, expected: str) -> None:
    assert normalize_git_remote(remote) == expected


def test_normalize_rejects_local_or_unsafe_paths() -> None:
    with pytest.raises(RepositoryIdentityError):
        normalize_git_remote("../repository")
    with pytest.raises(RepositoryIdentityError):
        normalize_git_remote("https://github.com/team/../repository.git")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_repository_identity_matches_across_clone_paths(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for repo in (first, second):
        _git(repo, "init")
        _git(repo, "remote", "add", "origin", "git@github.com:cyberDJs/CyberCore.git")

    assert repository_identity(first) == repository_identity(second)
    assert repository_identity(first) == "git:github.com/cyberDJs/CyberCore"


def test_repository_identity_uses_path_fallback_without_origin(tmp_path: Path) -> None:
    repo = tmp_path / "standalone"
    repo.mkdir()
    _git(repo, "init")

    assert repository_identity(repo) == f"path:{repo.resolve()}"


def test_repository_identity_uses_path_fallback_for_unsupported_origin(tmp_path: Path) -> None:
    repo = tmp_path / "unsupported"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "remote", "add", "origin", str(tmp_path / "bare.git"))

    assert repository_identity(repo) == f"path:{repo.resolve()}"
