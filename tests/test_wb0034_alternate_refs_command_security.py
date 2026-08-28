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


def _clear_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "GIT_DIR",
        "GIT_COMMON_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
        "GIT_CONFIG",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_PROXY_COMMAND",
        "GIT_EXEC_PATH",
        "GIT_SSL_NO_VERIFY",
        "GIT_SSL_CAINFO",
        "GIT_SSL_CAPATH",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(key, raising=False)


def test_wb0034_rejects_executable_alternate_refs_command_before_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_git_environment(monkeypatch)

    alternate = tmp_path / "alternate"
    alternate.mkdir()
    _git(alternate, "init", "-b", "main")

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "remote", "add", "origin", CANONICAL_HTTPS_ORIGIN)

    project = repo / ".cybercore" / "project.yaml"
    project.parent.mkdir(parents=True)
    project.write_text(
        f"version: 1\nidentity:\n  repository: {CANONICAL_IDENTITY}\n",
        encoding="utf-8",
    )

    alternates_file = repo / ".git" / "objects" / "info" / "alternates"
    alternates_file.parent.mkdir(parents=True, exist_ok=True)
    alternates_file.write_text(str(alternate / ".git" / "objects") + "\n", encoding="utf-8")

    marker = tmp_path / "alternate-refs-command-ran"
    _git(repo, "config", "core.alternateRefsCommand", f"touch {marker}")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport rewrite/override"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)

    assert not marker.exists()
