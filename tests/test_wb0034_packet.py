from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

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


def _evidence_text(source_commit: str) -> str:
    return f"""version: 1
evidence_class: wb0034_first_write
target_id: interserver-shared-hosting-staging
source_commit: {source_commit}
run_id: {RUN_ID}
destination: {DESTINATION}
artifacts:
  index.html: {'a' * 64}
  cybercore-version.json: {'b' * 64}
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


def _write_packet(repo: Path, source_commit: str) -> tuple[Path, Path, Path]:
    deploy = repo / ".cybercore/deploy"
    manifests = deploy / "manifests"
    readiness_dir = deploy / "readiness"
    evidence_dir = deploy / "evidence"
    manifests.mkdir(parents=True)
    readiness_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    evidence = evidence_dir / "wb0034-first-write.yaml"
    evidence.write_text(_evidence_text(source_commit), encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()

    manifest = manifests / "wb0034-final.yaml"
    manifest.write_text(_manifest_text(source_commit), encoding="utf-8")
    readiness = readiness_dir / "wb0034-final.yaml"
    readiness.write_text(_readiness_text(source_commit, digest), encoding="utf-8")
    return manifest, readiness, evidence


def test_final_packet_passes_only_when_all_artifacts_bind_to_repo_head(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _ = _write_packet(repo, head)

    result = validate_first_write_packet(manifest, readiness, repo)

    assert result.ready, result.as_text()


def test_final_packet_rejects_syntactically_valid_but_non_head_commit(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _ = _write_packet(repo, head)
    other_sha = "f" * 40
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(head, other_sha),
        encoding="utf-8",
    )

    result = validate_first_write_packet(manifest, readiness, repo)

    assert not result.ready
    assert any("checked-out repository HEAD" in error for error in result.errors)


def test_final_packet_rejects_manifest_evidence_run_id_mismatch(tmp_path: Path) -> None:
    repo, head = _init_repo(tmp_path)
    manifest, readiness, _ = _write_packet(repo, head)
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        .replace(f"run_id: {RUN_ID}", "run_id: 20260822T183501Z-d4e5f6")
        .replace(DESTINATION, "cybercore-canary-20260822T183501Z-d4e5f6/"),
        encoding="utf-8",
    )

    result = validate_first_write_packet(manifest, readiness, repo)

    assert not result.ready
    assert any("run_id" in error for error in result.errors)
