from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from cybercore.entrypoint import main
from cybercore.repository_identity import (
    RepositoryIdentityError,
    redact_git_remote,
    render_repository_identity,
    resolve_repository_identity,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo(tmp_path: Path, origin: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / ".cybercore").mkdir()
    (repo / ".cybercore" / "project.yaml").write_text("version: 1\n", encoding="utf-8")
    if origin is not None:
        _git(repo, "remote", "add", "origin", origin)
    return repo


def test_remote_diagnostic_exposes_normalized_identity(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "git@GitHub.com:cyberDJs/CyberCore.git")

    result = resolve_repository_identity(repo)

    assert result.source == "remote"
    assert result.identity == "git:github.com/cyberDJs/CyberCore"
    assert result.origin == "github.com:cyberDJs/CyberCore.git"
    assert "derived from origin" in result.diagnostic


def test_missing_origin_uses_explicit_path_fallback(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    result = resolve_repository_identity(repo)

    assert result.source == "path_fallback"
    assert result.identity == f"path:{repo.resolve()}"
    assert result.origin is None
    assert result.diagnostic == "No origin remote is configured."


def test_invalid_origin_reports_reason_without_leaking_value(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "file:///tmp/private.git")

    result = resolve_repository_identity(repo)

    assert result.source == "path_fallback"
    assert result.origin == "file://[REDACTED_PATH]"
    assert "Unsupported Git remote scheme" in result.diagnostic


def test_strict_mode_rejects_missing_origin(tmp_path: Path) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(RepositoryIdentityError, match="Remote repository identity required"):
        resolve_repository_identity(repo, strict=True)


def test_redaction_removes_http_credentials() -> None:
    remote = "https://operator:super-secret@GitHub.com/cyberDJs/CyberCore.git"

    redacted = redact_git_remote(remote)

    assert redacted == "https://github.com/cyberDJs/CyberCore.git"
    assert "operator" not in redacted
    assert "super-secret" not in redacted


def test_text_renderer_reports_contract_fields(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "https://github.com/cyberDJs/CyberCore.git")

    rendered = render_repository_identity(resolve_repository_identity(repo))

    assert "REPOSITORY IDENTITY" in rendered
    assert str(repo.resolve()) not in rendered
    assert "Identity: git:github.com/cyberDJs/CyberCore" in rendered
    assert "Source: remote" in rendered
    assert "Origin: https://github.com/cyberDJs/CyberCore.git" in rendered


def test_identity_default_text_redacts_path_fallback(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "identity"])
    rendered = capsys.readouterr().out

    assert exit_code == 0
    assert "Repository: [REDACTED]" in rendered
    assert "Identity: path:[REDACTED]" in rendered
    assert str(repo.resolve()) not in rendered


def test_identity_cli_supports_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(tmp_path, "https://token:secret@github.com/cyberDJs/CyberCore.git")

    exit_code = main(["--repo", str(repo), "--json", "identity"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["repository"] == "[REDACTED]"
    assert payload["source"] == "remote"
    assert payload["identity"] == "git:github.com/cyberDJs/CyberCore"
    assert payload["origin"] == "https://github.com/cyberDJs/CyberCore.git"
    assert "secret" not in json.dumps(payload)
    assert str(repo.resolve()) not in json.dumps(payload)


def test_identity_redacted_mode_hides_operational_identity(
    tmp_path: Path,
    capsys,
) -> None:
    repo = _repo(tmp_path, "https://github.com/cyberDJs/CyberCore.git")

    exit_code = main(["--repo", str(repo), "--json", "identity", "--redact"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["repository"] == "[REDACTED]"
    assert payload["identity"] == "[REDACTED]"
    assert payload["origin"] == "[REDACTED]"


def test_identity_full_mode_exposes_repository_path_explicitly(
    tmp_path: Path,
    capsys,
) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "--json", "identity", "--full"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["repository"] == str(repo.resolve())
    assert payload["identity"] == f"path:{repo.resolve()}"


def test_identity_default_json_redacts_path_fallback(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "--json", "identity"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["identity"] == "path:[REDACTED]"
    assert str(repo.resolve()) not in json.dumps(payload)


def test_identity_full_mode_never_emits_origin_credentials(
    tmp_path: Path,
    capsys,
) -> None:
    repo = _repo(tmp_path, "ssh://operator:secret@github.com/cyberDJs/CyberCore.git")

    exit_code = main(["--repo", str(repo), "--json", "identity", "--full"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["origin"] == "ssh://github.com/cyberDJs/CyberCore.git"
    assert "operator" not in json.dumps(payload)
    assert "secret" not in json.dumps(payload)


def test_identity_cli_strict_failure_is_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _repo(tmp_path)

    exit_code = main(["--repo", str(repo), "identity", "--strict"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Remote repository identity required" in captured.err
