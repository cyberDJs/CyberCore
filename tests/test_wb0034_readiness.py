from __future__ import annotations

from pathlib import Path

from cybercore.first_write import validate_first_write_readiness


ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
PINNED_SHA = "0123456789abcdef0123456789abcdef01234567"


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
            "evidence:wb0034:sftp-capability:2026-08-22",
        )
        .replace(
            "WB0034_DEPLOY_IDENTITY_SCOPE_VERIFICATION_REQUIRED",
            "evidence:wb0034:deploy-identity-scope:2026-08-22",
        )
        .replace("source_commit_reference: TBD", f"source_commit_reference: {PINNED_SHA}")
        .replace(
            "WB0034_ARTIFACT_HASHES_REQUIRED",
            "evidence:wb0034:artifact-sha256:2026-08-22",
        )
        .replace("rollback_tested: false", "rollback_tested: true")
        .replace(
            "WB0034_EFFECT_VERIFIER_IMPLEMENTATION_REQUIRED",
            "evidence:wb0034:effect-verifier-dry-run:2026-08-22",
        )
        .replace(
            "authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
            "authorization_reference: approval:jan-koci:wb0034:first-write",
        )
    )


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


def test_future_ready_artifact_can_pass_without_granting_remote_write(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_future_ready_text(), encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert result.schema_ok, result.as_text()
    assert result.ready, result.as_text()
    text = readiness.read_text(encoding="utf-8")
    assert "remote_write_requested: false" in text
    assert "remote_write_allowed: false" in text
    assert "production_write_allowed: false" in text
    assert "capability_evidence_remote_write_performed: false" in text


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


def test_readiness_rejects_plaintext_secret_literals(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8") + "\npassword: bad\n",
        encoding="utf-8",
    )

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("denied literal" in error for error in result.errors)
