from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from cybercore import first_write_packet as first_write_packet_module
from cybercore.first_write_packet import validate_first_write_packet


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TEMPLATE = ROOT / ".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml"
READINESS_TEMPLATE = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
RUN_ID = "20260822T183500Z-a1b2c3"
DESTINATION = f"cybercore-canary-{RUN_ID}/"
CAPABILITY_REF = "evidence:wb0034:sftp-capability:20260822"
SCOPE_REF = "evidence:wb0034:deploy-identity-scope:20260822"
ARTIFACT_REF = "evidence:wb0034:artifact-sha256:20260822"
VERIFIER_REF = "evidence:wb0034:effect-verifier:20260822"
AUTH_REF = "approval:wb0034:20260822T183500Z"
BUILT_AT = "2026-08-22T18:35:00Z"


@pytest.fixture(autouse=True)
def _isolate_packet_tests_from_repository_identity_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        first_write_packet_module,
        "enforce_configured_repository_identity_policy",
        lambda *_args, **_kwargs: None,
    )


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-b", "main")
    _run_git(repo, "config", "user.name", "WB0034 Test")
    _run_git(repo, "config", "user.email", "wb0034@example.invalid")
    (repo / "source.txt").write_text("deployment source\n", encoding="utf-8")
    _run_git(repo, "add", "source.txt")
    _run_git(repo, "commit", "-m", "test source")
    return repo, _run_git(repo, "rev-parse", "HEAD")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifacts(
    repo: Path,
    source_commit: str,
    *,
    marker_overrides: dict[str, object] | None = None,
    marker_drop_keys: set[str] | None = None,
) -> tuple[Path, dict[str, str]]:
    artifact_dir = repo / "build" / "wb0034"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "index.html").write_text(
        "<!doctype html><title>CyberCore canary</title>\n",
        encoding="utf-8",
    )

    marker: dict[str, object] = {
        "repository": "cyberDJs/CyberCore",
        "commit": source_commit,
        "branch": "main",
        "built_at": BUILT_AT,
        "environment": "interserver-shared-hosting-staging",
        "run_id": RUN_ID,
    }
    if marker_overrides:
        marker.update(marker_overrides)
    if marker_drop_keys:
        for key in marker_drop_keys:
            marker.pop(key, None)

    (artifact_dir / "cybercore-version.json").write_text(
        json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return artifact_dir, {
        "index.html": _sha256(artifact_dir / "index.html"),
        "cybercore-version.json": _sha256(artifact_dir / "cybercore-version.json"),
    }


def _evidence_text(
    source_commit: str,
    artifact_hashes: dict[str, str],
    *,
    authorization_protocol: str = "SFTP",
    authorization_scope: str = SCOPE_REF,
) -> str:
    return f"""version: 1
evidence_class: wb0034_first_write
target_id: interserver-shared-hosting-staging
source_commit: {source_commit}
run_id: {RUN_ID}
destination: {DESTINATION}
artifacts:
  index.html: {artifact_hashes["index.html"]}
  cybercore-version.json: {artifact_hashes["cybercore-version.json"]}
deployment:
  protocol: SFTP
  target_capability_reference: {CAPABILITY_REF}
  deploy_identity_scope_reference: {SCOPE_REF}
  production_write_excluded: true
  secret_values_recorded: false
  remote_write_performed: false
rollback:
  method: no_overwrite_unique_directory_scoped_delete_if_authorized
  tested: true
effect_verifier:
  verified: true
  reference: {VERIFIER_REF}
authorization:
  status: APPROVED
  reference: {AUTH_REF}
  source_commit: {source_commit}
  run_id: {RUN_ID}
  destination: {DESTINATION}
  artifacts:
    - index.html
    - cybercore-version.json
  protocol: {authorization_protocol}
  deploy_identity_scope_reference: {authorization_scope}
  rollback_permitted: true
secret_values_present: false
"""


def _manifest_text(source_commit: str) -> str:
    return (
        MANIFEST_TEMPLATE.read_text(encoding="utf-8")
        .replace("run_id: WB0034-FIRST-STAGING-WRITE-PLAN", f"run_id: {RUN_ID}")
        .replace("source_commit: TBD", f"source_commit: {source_commit}")
        .replace(
            "operator_authorization_reference: NOT_REQUIRED_FOR_PLAN_ONLY",
            f"operator_authorization_reference: {AUTH_REF}",
        )
        .replace(
            "planned_remote_destination: cybercore-canary-<run_id>/",
            f"planned_remote_destination: {DESTINATION}",
        )
    )


def _readiness_text(source_commit: str, digest: str) -> str:
    return (
        READINESS_TEMPLATE.read_text(encoding="utf-8")
        .replace("deployment_protocol_status: UNKNOWN", "deployment_protocol_status: VERIFIED")
        .replace("deployment_protocol: UNVERIFIED", "deployment_protocol: SFTP")
        .replace("target_capability_status: UNKNOWN", "target_capability_status: VERIFIED")
        .replace("deploy_identity_scope_status: UNKNOWN", "deploy_identity_scope_status: VERIFIED")
        .replace(
            "WB0034_DEPLOYMENT_PROTOCOL_READ_ONLY_VERIFICATION_REQUIRED",
            CAPABILITY_REF,
        )
        .replace(
            "WB0034_DEPLOY_IDENTITY_SCOPE_VERIFICATION_REQUIRED",
            SCOPE_REF,
        )
        .replace("source_commit_status: UNKNOWN", "source_commit_status: PINNED")
        .replace("source_commit_reference: TBD", f"source_commit_reference: {source_commit}")
        .replace("artifact_hashes_status: UNKNOWN", "artifact_hashes_status: VERIFIED")
        .replace("WB0034_ARTIFACT_HASHES_REQUIRED", ARTIFACT_REF)
        .replace("secret_alias_status: UNKNOWN", "secret_alias_status: VERIFIED")
        .replace("rollback_status: UNKNOWN", "rollback_status: VERIFIED")
        .replace("rollback_tested: false", "rollback_tested: true")
        .replace("effect_verifier_status: UNKNOWN", "effect_verifier_status: VERIFIED")
        .replace("WB0034_EFFECT_VERIFIER_IMPLEMENTATION_REQUIRED", VERIFIER_REF)
        .replace(
            "operator_authorization_status: UNKNOWN",
            "operator_authorization_status: APPROVED",
        )
        .replace(
            "authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
            f"authorization_reference: {AUTH_REF}",
        )
        .replace(
            "evidence_bundle_reference: WB0034_EVIDENCE_BUNDLE_REQUIRED",
            "evidence_bundle_reference: ../evidence/wb0034-first-write.yaml",
        )
        .replace("evidence_bundle_sha256: TBD", f"evidence_bundle_sha256: {digest}")
    )


def _write_packet(
    repo: Path,
    source_commit: str,
    *,
    authorization_protocol: str = "SFTP",
    authorization_scope: str = SCOPE_REF,
    marker_overrides: dict[str, object] | None = None,
    marker_drop_keys: set[str] | None = None,
) -> tuple[Path, Path, Path, Path]:
    deploy = repo / ".cybercore/deploy"
    manifests = deploy / "manifests"
    readiness_dir = deploy / "readiness"
    evidence_dir = deploy / "evidence"
    manifests.mkdir(parents=True)
    readiness_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    artifact_dir, artifact_hashes = _write_artifacts(
        repo,
        source_commit,
        marker_overrides=marker_overrides,
        marker_drop_keys=marker_drop_keys,
    )

    evidence = evidence_dir / "wb0034-first-write.yaml"
    evidence.write_text(
        _evidence_text(
            source_commit,
            artifact_hashes,
            authorization_protocol=authorization_protocol,
            authorization_scope=authorization_scope,
        ),
        encoding="utf-8",
    )
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()

    manifest = manifests / "wb0034-final.yaml"
    manifest.write_text(_manifest_text(source_commit), encoding="utf-8")
    readiness = readiness_dir / "wb0034-final.yaml"
    readiness.write_text(_readiness_text(source_commit, digest), encoding="utf-8")
    return manifest, readiness, evidence, artifact_dir


def test_final_packet_passes_only_when_all_artifacts_bind_to_main_head(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert result.ready, result.as_text()
    assert result.upload_input is not None


def test_ready_packet_carries_immutable_validated_upload_bytes(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert result.ready, result.as_text()
    assert result.upload_input is not None
    sealed_index = result.upload_input.artifact_bytes("index.html")
    (artifact_dir / "index.html").write_text("mutated after preflight\n", encoding="utf-8")
    assert result.upload_input.artifact_bytes("index.html") == sealed_index
    assert result.upload_input.destination == DESTINATION
    assert result.upload_input.source_commit == head


def test_final_packet_uses_private_snapshots_if_source_paths_change_after_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    original_validator = first_write_packet_module.validate_first_write_manifest
    mutated = False

    def mutate_sources_then_validate(
        snapshot_path: Path,
        *,
        final_preflight: bool = False,
    ):
        nonlocal mutated
        if not mutated:
            mutated = True
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "production_write_allowed: false",
                    "production_write_allowed: true",
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                readiness.read_text(encoding="utf-8").replace(
                    "production_write_allowed: false",
                    "production_write_allowed: true",
                ),
                encoding="utf-8",
            )
        return original_validator(snapshot_path, final_preflight=final_preflight)

    monkeypatch.setattr(
        first_write_packet_module,
        "validate_first_write_manifest",
        mutate_sources_then_validate,
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert result.ready, result.as_text()
    assert result.upload_input is not None
    assert "production_write_allowed: true" in manifest.read_text(encoding="utf-8")
    assert "production_write_allowed: true" in readiness.read_text(encoding="utf-8")
    assert result.upload_input.destination == DESTINATION


def test_final_packet_rejects_directory_change_during_artifact_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    real_listdir = first_write_packet_module.os.listdir
    directory_reads = 0

    def changing_listdir(path: int | str | bytes | os.PathLike[str] | os.PathLike[bytes]):
        nonlocal directory_reads
        entries = real_listdir(path)
        if isinstance(path, int):
            directory_reads += 1
            if directory_reads == 2:
                return [*entries, "unexpected-after-read.tmp"]
        return entries

    monkeypatch.setattr(first_write_packet_module.os, "listdir", changing_listdir)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert result.upload_input is None
    assert any(
        "changed during validation" in error or "after reads contains unexpected" in error
        for error in result.errors
    )


def test_final_packet_rejects_syntactically_valid_but_non_head_commit(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    other_sha = "f" * 40
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(head, other_sha),
        encoding="utf-8",
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("checked-out repository HEAD" in error for error in result.errors)


def test_final_packet_rejects_feature_branch_head_even_when_packet_matches_it(
    tmp_path: Path,
) -> None:
    repo, _ = _init_repo(tmp_path)
    _run_git(repo, "switch", "-c", "feature")
    (repo / "source.txt").write_text("feature deployment source\n", encoding="utf-8")
    _run_git(repo, "add", "source.txt")
    _run_git(repo, "commit", "-m", "feature source")
    feature_head = _run_git(repo, "rev-parse", "HEAD")
    manifest, readiness, _, artifact_dir = _write_packet(repo, feature_head)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("trusted main commit" in error for error in result.errors)


def test_final_packet_rejects_manifest_evidence_run_id_mismatch(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        .replace(f"run_id: {RUN_ID}", "run_id: 20260822T183501Z-d4e5f6")
        .replace(DESTINATION, "cybercore-canary-20260822T183501Z-d4e5f6/"),
        encoding="utf-8",
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("run_id" in error for error in result.errors)


def test_final_packet_rejects_authorization_protocol_mismatch(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        authorization_protocol="SSH",
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("authorization protocol" in error for error in result.errors)


def test_final_packet_rejects_authorization_identity_scope_mismatch(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        authorization_scope="evidence:wb0034:deploy-identity-scope:other",
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("authorization deploy identity scope" in error for error in result.errors)


def test_final_packet_rejects_local_artifact_tampering(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    (artifact_dir / "index.html").write_text("tampered\n", encoding="utf-8")

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("artifact digest mismatch: index.html" in error for error in result.errors)


def test_final_packet_rejects_symlinked_local_artifact(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    target = artifact_dir / "real-index.html"
    target.write_text("replacement\n", encoding="utf-8")
    (artifact_dir / "index.html").unlink()
    (artifact_dir / "index.html").symlink_to(target.name)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any(
        "without following links index.html" in error or "unexpected entries" in error
        for error in result.errors
    )


def test_final_packet_rejects_symlinked_artifact_directory_ancestor(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(repo, head)
    real_build = repo / "real-build"
    (repo / "build").rename(real_build)
    (repo / "build").symlink_to(real_build.name, target_is_directory=True)

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("artifact directory contains a symlink" in error for error in result.errors)


def test_final_packet_rejects_version_marker_commit_mismatch_with_matching_digest(
    tmp_path: Path,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        marker_overrides={"commit": "f" * 40},
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("cybercore-version.json commit" in error for error in result.errors)


def test_final_packet_rejects_version_marker_run_id_mismatch_with_matching_digest(
    tmp_path: Path,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        marker_overrides={"run_id": "20260822T183501Z-d4e5f6"},
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("cybercore-version.json run_id" in error for error in result.errors)


def test_final_packet_rejects_version_marker_environment_mismatch_with_matching_digest(
    tmp_path: Path,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        marker_overrides={"environment": "production"},
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("cybercore-version.json environment" in error for error in result.errors)


def test_final_packet_rejects_incomplete_version_marker_schema_with_matching_digest(
    tmp_path: Path,
) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _, artifact_dir = _write_packet(
        repo,
        head,
        marker_drop_keys={"environment"},
    )

    result = validate_first_write_packet(manifest, readiness, repo, artifact_dir)

    assert not result.ready
    assert any("cybercore-version.json is missing keys" in error for error in result.errors)
