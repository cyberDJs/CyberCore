from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import pytest

from cybercore.checkpoint import collect_checkpoint
from cybercore.verification_evidence import (
    VerificationEvidence,
    VerificationEvidenceError,
    repository_evidence_binding,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "CyberCore Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("verification\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "verification target")
    return tmp_path


def _payload(repo: Path, commit: str) -> dict[str, object]:
    return {
        "command": "pytest -q",
        "exit_code": 0,
        "duration": 4.25,
        "summary": "26 passed",
        "repository": str(repo.resolve()),
        "commit": commit,
        "generated_at": "2026-07-29T21:00:00Z",
    }


def _binding_payload(repo: Path, commit: str) -> dict[str, object]:
    payload = _payload(repo, commit)
    payload.pop("repository")
    payload["repository_binding"] = repository_evidence_binding(repo)
    return payload


def test_load_and_validate_successful_evidence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(
        repo, now=datetime(2026, 7, 29, 21, 0, tzinfo=timezone.utc)
    )
    path = repo / "evidence.json"
    path.write_text(json.dumps(_payload(repo, checkpoint.commit)), encoding="utf-8")

    evidence = VerificationEvidence.from_file(path)
    evidence.validate_for(checkpoint)

    assert evidence.exit_code == 0
    assert evidence.checkpoint_summary() == "26 passed via `pytest -q` in 4.25s"


def test_load_and_validate_successful_bound_evidence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    evidence = VerificationEvidence.from_dict(_binding_payload(repo, checkpoint.commit))

    evidence.validate_for(checkpoint)

    assert evidence.repository_binding == repository_evidence_binding(repo)


def test_legacy_evidence_summary_is_sanitized_when_loaded(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["summary"] = (
        f"checked {repo.resolve()} with "
        "https://user:password@example.test/repo?token=tokensecret123 "
        "token=abc123"
    )

    evidence = VerificationEvidence.from_dict(payload)

    assert str(repo.resolve()) not in evidence.summary
    assert "user:password" not in evidence.summary
    assert "tokensecret123" not in evidence.summary
    assert "abc123" not in evidence.summary


def test_legacy_evidence_checkpoint_summary_is_sanitized(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["summary"] = (
        f"checked {repo.resolve()} with "
        "https://user:password@example.test/repo?api_key=tokensecret123"
    )

    summary = VerificationEvidence.from_dict(payload).checkpoint_summary()

    assert str(repo.resolve()) not in summary
    assert "user:password" not in summary
    assert "tokensecret123" not in summary
    assert "[REDACTED_PATH]" in summary


def test_legacy_evidence_command_redacts_token_pair(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["command"] = "python -m pytest --token abc123 tests"

    evidence = VerificationEvidence.from_dict(payload)

    assert evidence.command == "python -m pytest --token [REDACTED] tests"
    assert "abc123" not in evidence.command


def test_legacy_evidence_command_redacts_quoted_password_with_spaces(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["command"] = 'deploy --password "hunter 2" --dry-run'

    evidence = VerificationEvidence.from_dict(payload)

    assert evidence.command == "deploy --password [REDACTED] --dry-run"
    assert "hunter" not in evidence.command
    assert "2" not in evidence.command


def test_legacy_evidence_command_redacts_url_credentials_and_query_token(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["command"] = (
        "curl https://user:password@example.test/repo?token=tokensecret123 "
        "--api-key=secret"
    )

    evidence = VerificationEvidence.from_dict(payload)

    assert "user:password" not in evidence.command
    assert "tokensecret123" not in evidence.command
    assert "secret" not in evidence.command
    assert "https://example.test/repo?token=[REDACTED]" in evidence.command
    assert "--api-key=[REDACTED]" in evidence.command


def test_legacy_evidence_normal_pytest_command_remains_unchanged(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)

    evidence = VerificationEvidence.from_dict(payload)

    assert evidence.command == "pytest -q"


def test_legacy_evidence_checkpoint_summary_never_emits_command_secrets(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["command"] = (
        f"pytest {repo.resolve()} --token abc123 "
        "https://user:password@example.test/repo?access_token=tokensecret123"
    )

    summary = VerificationEvidence.from_dict(payload).checkpoint_summary()

    assert str(repo.resolve()) not in summary
    assert "abc123" not in summary
    assert "user:password" not in summary
    assert "tokensecret123" not in summary
    assert "[REDACTED_PATH]" in summary


def test_legacy_evidence_invalid_shell_command_falls_back_safely(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["command"] = 'pytest --password "unterminated secret'

    evidence = VerificationEvidence.from_dict(payload)

    assert "unterminated secret" not in evidence.command
    assert evidence.command == 'pytest --password "[REDACTED]"'


def test_normal_evidence_summary_remains_unchanged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _binding_payload(repo, checkpoint.commit)
    payload["summary"] = "163 passed"

    evidence = VerificationEvidence.from_dict(payload)

    assert evidence.summary == "163 passed"


def test_rejects_failed_verification_command(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["exit_code"] = 1
    evidence = VerificationEvidence.from_dict(payload)

    with pytest.raises(VerificationEvidenceError, match="failed with exit code 1"):
        evidence.validate_for(checkpoint)


def test_rejects_repository_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _payload(repo, checkpoint.commit)
    payload["repository"] = str(repo / "other")
    evidence = VerificationEvidence.from_dict(payload)

    with pytest.raises(VerificationEvidenceError, match="repository does not match"):
        evidence.validate_for(checkpoint)


def test_rejects_repository_binding_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    payload = _binding_payload(repo, checkpoint.commit)
    payload["repository_binding"] = repository_evidence_binding(repo / "other")
    evidence = VerificationEvidence.from_dict(payload)

    with pytest.raises(VerificationEvidenceError, match="repository does not match"):
        evidence.validate_for(checkpoint)


def test_rejects_commit_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = collect_checkpoint(repo)
    evidence = VerificationEvidence.from_dict(_payload(repo, "0" * 40))

    with pytest.raises(VerificationEvidenceError, match="commit does not match"):
        evidence.validate_for(checkpoint)


def test_rejects_missing_required_fields() -> None:
    with pytest.raises(VerificationEvidenceError, match="missing fields"):
        VerificationEvidence.from_dict({"command": "pytest -q"})
