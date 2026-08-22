from __future__ import annotations

import hashlib
from pathlib import Path

from cybercore.first_write import validate_first_write_readiness


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"
RUN_ID = "20260822T183500Z-a1b2c3"
DESTINATION = f"cybercore-canary-{RUN_ID}/"
CAPABILITY_REF = "evidence:wb0034:sftp-capability:20260822"
SCOPE_REF = "evidence:wb0034:deploy-identity-scope:20260822"
ARTIFACT_REF = "evidence:wb0034:artifact-sha256:20260822"
VERIFIER_REF = "evidence:wb0034:effect-verifier:20260822"
AUTH_REF = "approval:wb0034:20260822T183500Z"


def _status_only_ready_text() -> str:
    return (
        READINESS.read_text(encoding="utf-8")
        .replace("deployment_protocol_status: UNKNOWN", "deployment_protocol_status: VERIFIED")
        .replace("target_capability_status: UNKNOWN", "target_capability_status: VERIFIED")
        .replace("deploy_identity_scope_status: UNKNOWN", "deploy_identity_scope_status: VERIFIED")
        .replace("source_commit_status: UNKNOWN", "source_commit_status: PINNED")
        .replace("artifact_hashes_status: UNKNOWN", "artifact_hashes_status: VERIFIED")
        .replace("secret_alias_status: UNKNOWN", "secret_alias_status: VERIFIED")
        .replace("rollback_status: UNKNOWN", "rollback_status: VERIFIED")
        .replace("effect_verifier_status: UNKNOWN", "effect_verifier_status: VERIFIED")
        .replace(
            "operator_authorization_status: UNKNOWN",
            "operator_authorization_status: APPROVED",
        )
    )


def _future_ready_text() -> str:
    return (
        _status_only_ready_text()
        .replace("deployment_protocol: UNVERIFIED", "deployment_protocol: SFTP")
        .replace(
            "WB0034_DEPLOYMENT_PROTOCOL_READ_ONLY_VERIFICATION_REQUIRED",
            CAPABILITY_REF,
        )
        .replace(
            "WB0034_DEPLOY_IDENTITY_SCOPE_VERIFICATION_REQUIRED",
            SCOPE_REF,
        )
        .replace("source_commit_reference: TBD", f"source_commit_reference: {PINNED_SHA}")
        .replace("WB0034_ARTIFACT_HASHES_REQUIRED", ARTIFACT_REF)
        .replace("rollback_tested: false", "rollback_tested: true")
        .replace("WB0034_EFFECT_VERIFIER_IMPLEMENTATION_REQUIRED", VERIFIER_REF)
        .replace(
            "authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
            f"authorization_reference: {AUTH_REF}",
        )
    )


def _evidence_text() -> str:
    return f"""version: 1
evidence_class: wb0034_first_write
target_id: interserver-shared-hosting-staging
source_commit: {PINNED_SHA}
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
  source_commit: {PINNED_SHA}
  run_id: {RUN_ID}
  destination: {DESTINATION}
  artifacts:
    - index.html
    - cybercore-version.json
  rollback_permitted: true
secret_values_present: false
"""


def _write_bound_readiness(tmp_path: Path) -> tuple[Path, Path]:
    deploy = tmp_path / "deploy"
    readiness_dir = deploy / "readiness"
    evidence_dir = deploy / "evidence"
    readiness_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    evidence = evidence_dir / "wb0034-first-write.yaml"
    evidence.write_text(_evidence_text(), encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()

    readiness = readiness_dir / "readiness.yaml"
    readiness.write_text(
        _future_ready_text()
        .replace(
            "evidence_bundle_reference: WB0034_EVIDENCE_BUNDLE_REQUIRED",
            "evidence_bundle_reference: ../evidence/wb0034-first-write.yaml",
        )
        .replace("evidence_bundle_sha256: TBD", f"evidence_bundle_sha256: {digest}"),
        encoding="utf-8",
    )
    return readiness, evidence


def test_current_wb0034_readiness_is_schema_valid_but_blocked() -> None:
    result = validate_first_write_readiness(READINESS)

    assert result.schema_ok, result.as_text()
    assert not result.ready
    assert any("deployment_protocol_status" in blocker for blocker in result.blockers)
    assert any("deploy_identity_scope_status" in blocker for blocker in result.blockers)
    assert any("operator_authorization_status" in blocker for blocker in result.blockers)


def test_status_labels_alone_cannot_clear_readiness_gate(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_status_only_ready_text(), encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert not result.ready
    assert any("deployment_protocol SFTP or SSH" in blocker for blocker in result.blockers)
    assert any("capability evidence" in blocker for blocker in result.blockers)
    assert any("scope evidence" in blocker for blocker in result.blockers)
    assert any("40-character commit SHA" in blocker for blocker in result.blockers)
    assert any("artifact hash evidence" in blocker for blocker in result.blockers)
    assert any("rollback_tested" in blocker for blocker in result.blockers)
    assert any("verifier evidence" in blocker for blocker in result.blockers)
    assert any("authorization reference" in blocker for blocker in result.blockers)


def test_arbitrary_evidence_references_cannot_clear_gate_without_bundle(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_future_ready_text(), encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert not result.ready
    assert any("evidence bundle" in blocker for blocker in result.blockers)


def test_hash_bound_evidence_bundle_can_clear_component_readiness(tmp_path: Path) -> None:
    readiness, _ = _write_bound_readiness(tmp_path)

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert result.ready, result.as_text()
    text = readiness.read_text(encoding="utf-8")
    assert "remote_write_requested: false" in text
    assert "remote_write_allowed: false" in text
    assert "production_write_allowed: false" in text
    assert "capability_evidence_remote_write_performed: false" in text


def test_evidence_bundle_hash_mismatch_blocks_readiness(tmp_path: Path) -> None:
    readiness, evidence = _write_bound_readiness(tmp_path)
    evidence.write_text(_evidence_text().replace("protocol: SFTP", "protocol: SSH"), encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert not result.ready
    assert any("sha256" in blocker for blocker in result.blockers)


def test_readiness_rejects_production_url_verifier_requirement(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8").replace(
            "write_scope_matches_approved_staging_destination",
            "production_url_is_unchanged",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("required_checks" in error for error in result.errors)


def test_readiness_requires_deploy_identity_scope_gate(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8").replace(
            "  deploy_identity_scope_status: UNKNOWN\n",
            "",
        ),
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok
    assert not result.ready
    assert any("deploy_identity_scope_status" in blocker for blocker in result.blockers)


def test_readiness_rejects_plaintext_secret_assignment(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8") + "\npassword: bad\n",
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("credential-like assignment" in error for error in result.errors)


def test_readiness_rejects_secret_bearing_comment(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8")
        + "\n# credential https://alice:hunter2@example.com\n",
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("forbids YAML comments" in error for error in result.errors)
