from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore.repository_identity_policy import (
    RepositoryIdentityPolicyError,
    enforce_configured_repository_identity_policy,
)


OPERATION = "WB-0034 trusted-main resolution"
CANONICAL_IDENTITY = "git:github.com/cyberDJs/CyberCore"
CANONICAL_HTTPS_ORIGIN = "https://github.com/cyberDJs/CyberCore.git"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_wb0034_rejects_git_config_file_that_hides_local_transport_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in (
        "GIT_DIR",
        "GIT_COMMON_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
        "GIT_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "remote", "add", "origin", CANONICAL_HTTPS_ORIGIN)
    _git(repo, "config", "remote.origin.vcs", "ext")
    _git(repo, "config", "protocol.ext.allow", "always")

    project = repo / ".cybercore" / "project.yaml"
    project.parent.mkdir(parents=True)
    project.write_text(
        f"version: 1\nidentity:\n  repository: {CANONICAL_IDENTITY}\n",
        encoding="utf-8",
    )

    clean_config = tmp_path / "clean-git-config"
    clean_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG", str(clean_config))

    # GIT_CONFIG makes `git config --get remote.origin.vcs` read only the clean
    # file, while other Git commands still honor the repository-local config.
    # WB-0034 must therefore reject the environment before policy queries run.
    with pytest.raises(RepositoryIdentityPolicyError, match="config-selection"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)
