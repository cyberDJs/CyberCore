from __future__ import annotations

import hashlib
from pathlib import Path

from cybercore.first_write import validate_first_write_readiness
from cybercore.first_write_evidence import (
    EXPECTED_INDEX_HTML_SHA256,
    validate_first_write_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"
RUN_ID = "20260829T120000Z-ftps01"
DESTINATION = f"cybercore-canary-{RUN_ID}/"
CAPABILITY_REF = "evidence:wb0034:ftps-explicit-capability:20260829"
SCOPE_REF = "evidence:wb0034:ftps-path-scope:20260829"
ARTIFACT_REF = "evidence:wb0034:artifact-sha256:20260829"
VERIFIER_REF = "evidence:wb0034:effect-verifier:20260829"
AUTH_REF = "approval:wb0034:20260829T120000Z-ftps01"


def _evidence_text(protocol: str) -> str:
    return f"""version: 1
evidence_class: wb0034_first_write
target_id: interserver-shared-hosting-staging
source_commit: {PINNED_SHA}
run_id: {RUN_ID}
destination: {DESTINATION}
artifacts:
  index.html: {EXPECTED_INDEX_HTML_SHA256}
  cybercore-version.json: {"b" * 64}
deployment:
  protocol: {protocol}
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
  protocol: {protocol}
  deploy_identity_scope_reference: {SCOPE_REF}
  rollback_permitted: true
secret_values_present: false
"""


def _ready_text(evidence_digest: str) -> str:
    return (
        READINESS.read_text(encoding="utf-8")
        .replace("deployment_protocol_status: UNKNOWN", "deployment_protocol_status: VERIFIED")
        .replace("deployment_protocol: UNVERIFIED", "deployment_protocol: FTPS_EXPLICIT")
        .replace("target_capability_status: UNKNOWN", "target_capability_status: VERIFIED")
        .replace("deploy_identity_scope_status: UNKNOWN", "deploy_identity_scope_status: VERIFIED")
        .replace("source_commit_status: UNKNOWN", "source_commit_status: PINNED")
        .replace("artifact_hashes_status: UNKNOWN", "artifact_hashes_status: VERIFIED")
        .replace("secret_alias_status: UNKNOWN", "secret_alias_status: VERIFIED")
        .replace("rollback_status: UNKNOWN", "rollback_status: VERIFIED")
        .replace("effect_verifier_status: UNKNOWN", "effect_verifier_status: VERIFIED")
        .replace(
            "operator_authorization_status: UNKNOWN", "operator_authorization_status: APPROVED"
        )
        .replace("WB0034_DEPLOYMENT_PROTOCOL_READ_ONLY_VERIFICATION_REQUIRED", CAPABILITY_REF)
        .replace("WB0034_DEPLOY_IDENTITY_SCOPE_VERIFICATION_REQUIRED", SCOPE_REF)
        .replace("source_commit_reference: TBD", f"source_commit_reference: {PINNED_SHA}")
        .replace("WB0034_ARTIFACT_HASHES_REQUIRED", ARTIFACT_REF)
        .replace("rollback_tested: false", "rollback_tested: true")
        .replace("WB0034_EFFECT_VERIFIER_IMPLEMENTATION_REQUIRED", VERIFIER_REF)
        .replace(
            "authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
            f"authorization_reference: {AUTH_REF}",
        )
        .replace(
            "evidence_bundle_reference: WB0034_EVIDENCE_BUNDLE_REQUIRED",
            "evidence_bundle_reference: ../evidence/wb0034-ftps.yaml",
        )
        .replace("evidence_bundle_sha256: TBD", f"evidence_bundle_sha256: {evidence_digest}")
    )


def test_explicit_ftps_is_accepted_by_evidence_validator(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.yaml"
    evidence.write_text(_evidence_text("FTPS_EXPLICIT"), encoding="utf-8")

    result = validate_first_write_evidence(evidence)

    assert result.ok, result.as_text()
    assert result.protocol == "FTPS_EXPLICIT"


def test_plain_ftp_is_rejected_by_evidence_validator(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.yaml"
    evidence.write_text(_evidence_text("FTP"), encoding="utf-8")

    result = validate_first_write_evidence(evidence)

    assert not result.ok
    assert any("FTPS_EXPLICIT" in error for error in result.errors)


def test_implicit_ftps_is_rejected_by_evidence_validator(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.yaml"
    evidence.write_text(_evidence_text("FTPS_IMPLICIT"), encoding="utf-8")

    result = validate_first_write_evidence(evidence)

    assert not result.ok
    assert any("FTPS_EXPLICIT" in error for error in result.errors)


def test_hash_bound_explicit_ftps_can_clear_component_readiness(tmp_path: Path) -> None:
    deploy = tmp_path / "deploy"
    readiness_dir = deploy / "readiness"
    evidence_dir = deploy / "evidence"
    readiness_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    evidence = evidence_dir / "wb0034-ftps.yaml"
    evidence.write_text(_evidence_text("FTPS_EXPLICIT"), encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()

    readiness = readiness_dir / "readiness.yaml"
    readiness.write_text(_ready_text(digest), encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert result.ready, result.as_text()
    assert "remote_write_allowed: false" in readiness.read_text(encoding="utf-8")
    assert "production_write_allowed: false" in readiness.read_text(encoding="utf-8")
