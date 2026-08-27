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


def _repo(tmp_path: Path, *, origin: str = CANONICAL_HTTPS_ORIGIN) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "remote", "add", "origin", origin)
    project = repo / ".cybercore" / "project.yaml"
    project.parent.mkdir(parents=True)
    project.write_text(
        f"version: 1\nidentity:\n  repository: {CANONICAL_IDENTITY}\n",
        encoding="utf-8",
    )
    return repo


def _clear_transport_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
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


def test_wb0034_accepts_canonical_https_transport_without_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)

    result = enforce_configured_repository_identity_policy(repo, operation=OPERATION)

    assert result is not None
    assert result.compliant


def test_wb0034_rejects_canonical_identity_over_ssh_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path, origin="git@github.com:cyberDJs/CyberCore.git")

    with pytest.raises(RepositoryIdentityPolicyError, match="canonical GitHub HTTPS origin"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_repository_local_ssh_command_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    _git(repo, "config", "core.sshCommand", "/tmp/attacker-controlled-ssh")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport rewrite/override"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_remote_vcs_helper_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    _git(repo, "config", "remote.origin.vcs", "ext")
    _git(repo, "config", "protocol.ext.allow", "always")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport rewrite/override"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_protocol_helper_allow_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    _git(repo, "config", "protocol.ext.allow", "always")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport rewrite/override"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_git_url_rewrite_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    _git(repo, "config", "url.file:///tmp/attacker/.insteadOf", "https://github.com/")

    with pytest.raises(
        RepositoryIdentityPolicyError,
        match="canonical GitHub HTTPS origin|transport rewrite/override|path fallback",
    ):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_inherited_git_ssh_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    monkeypatch.setenv("GIT_SSH_COMMAND", "/tmp/attacker-controlled-ssh")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport overrides"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_inherited_git_exec_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    monkeypatch.setenv("GIT_EXEC_PATH", "/tmp/attacker-controlled-git-core")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport overrides"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)


def test_wb0034_rejects_disabled_git_tls_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_transport_env(monkeypatch)
    repo = _repo(tmp_path)
    monkeypatch.setenv("GIT_SSL_NO_VERIFY", "1")

    with pytest.raises(RepositoryIdentityPolicyError, match="transport overrides"):
        enforce_configured_repository_identity_policy(repo, operation=OPERATION)
