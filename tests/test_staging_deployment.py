from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from cybercore.deployment.staging import (
    StagingValidationError,
    assess_target,
    build_manifest,
    load_target,
)

TARGET = (
    Path(__file__).resolve().parents[1]
    / ".cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml"
)
SHA = "a" * 40


def _target() -> dict[str, object]:
    return load_target(TARGET)


def test_plan_only_accepts_draft_but_keeps_remote_write_denied() -> None:
    result = assess_target(_target(), mode="plan_only")
    assert result.remote_write_allowed is False
    assert result.ready is False
    assert result.plan_status == "BLOCKED"
    assert "staging_identity.domain_or_url" in result.unresolved_gates
    assert "rollback.verified_mode" in result.unresolved_gates
    assert "effect_verifier.status" in result.unresolved_gates
    assert "secret_policy.alias_verification_status" in result.unresolved_gates


def test_dry_run_fails_closed_on_unresolved_target() -> None:
    with pytest.raises(StagingValidationError, match="dry_run target gates unresolved"):
        assess_target(_target(), mode="dry_run")


@pytest.mark.parametrize(
    "mode", ["staging_apply", "staging_apply_after_explicit_operator_approval"]
)
def test_remote_modes_are_never_authorized_in_this_slice(mode: str) -> None:
    with pytest.raises(StagingValidationError, match="not authorized"):
        assess_target(_target(), mode=mode)


def test_target_id_and_environment_are_locked_to_staging() -> None:
    target = _target()
    target["target_id"] = "production"
    with pytest.raises(StagingValidationError, match="target_id"):
        assess_target(target, mode="plan_only")

    target = _target()
    target["environment_class"] = "production"
    with pytest.raises(StagingValidationError, match="environment_class"):
        assess_target(target, mode="plan_only")


def test_production_and_provider_boundaries_cannot_be_weakened() -> None:
    for field, message in (
        ("production_mutation_allowed", "production mutation"),
        ("production_credentials_allowed", "production credentials"),
        ("provider_mutation_allowed_without_explicit_approval", "provider mutation"),
    ):
        target = _target()
        target["production_boundary"][field] = True
        with pytest.raises(StagingValidationError, match=message):
            assess_target(target, mode="plan_only")


def test_live_deploy_gate_and_user_scope_must_remain_locked() -> None:
    target = _target()
    target["current_gate_state"]["live_staging_deploy"] = "ready"
    with pytest.raises(StagingValidationError, match="live_staging_deploy"):
        assess_target(target, mode="plan_only")

    target = _target()
    target["staging_identity"]["deployment_user_scope"] = "account_wide"
    with pytest.raises(StagingValidationError, match="deployment_user_scope"):
        assess_target(target, mode="plan_only")


def test_production_domain_cannot_be_used_as_staging_target() -> None:
    target = _target()
    target["staging_identity"]["domain_or_url"] = "https://eimyherrer.com/preview"
    with pytest.raises(StagingValidationError, match="denied production domain"):
        assess_target(target, mode="plan_only")


def test_secret_value_fields_are_rejected_but_alias_metadata_is_allowed(tmp_path: Path) -> None:
    target = _target()
    assert target["secret_policy"]["required_secret_aliases"]

    target["secret_policy"]["password"] = "do-not-store-this"
    path = tmp_path / "target.yaml"
    path.write_text(yaml.safe_dump(target), encoding="utf-8")
    with pytest.raises(StagingValidationError, match="sensitive value field"):
        load_target(path)


def test_unapproved_secret_store_is_rejected() -> None:
    target = _target()
    target["secret_policy"]["approved_secret_locations"].append("github_environment_secret")
    with pytest.raises(StagingValidationError, match="unauthorized store"):
        assess_target(target, mode="plan_only")


def test_verified_local_dry_run_can_become_ready_without_remote_authority() -> None:
    target = deepcopy(_target())
    target["staging_identity"].update(
        {
            "domain_or_url": "https://staging.example.test",
            "document_root": "/home/staging/public_html",
            "capability_status": "VERIFIED_LOCAL_CONTRACT",
        }
    )
    target["rollback"]["verified_mode"] = "timestamped_backup_before_overwrite"
    target["effect_verifier"] = {"status": "verified", "reference": "local-contract"}
    target["secret_policy"]["alias_verification_status"] = "verified"

    result = assess_target(target, mode="dry_run")
    assert result.ready is True
    assert result.plan_status == "DRY_RUN_READY"
    assert result.remote_write_allowed is False
    assert result.unresolved_gates == ()


def test_manifest_is_local_only_and_validates_source_identity() -> None:
    result = assess_target(_target(), mode="plan_only")
    manifest = build_manifest(
        result,
        run_id="run-1",
        repository="cyberDJs/CyberCore",
        source_branch="main",
        source_commit=SHA,
        artifact_identity="source-tree",
        evidence_destination="evidence/staging-manifest.json",
    )
    assert manifest.remote_write_allowed is False
    assert manifest.plan_status == "BLOCKED"
    assert manifest.target_id == "interserver-shared-hosting-staging"

    with pytest.raises(StagingValidationError, match="40-character"):
        build_manifest(
            result,
            run_id="run-2",
            repository="cyberDJs/CyberCore",
            source_branch="main",
            source_commit="abc",
            artifact_identity="source-tree",
            evidence_destination="staging-manifest.json",
        )

    with pytest.raises(StagingValidationError, match="safe relative path"):
        build_manifest(
            result,
            run_id="run-3",
            repository="cyberDJs/CyberCore",
            source_branch="main",
            source_commit=SHA,
            artifact_identity="source-tree",
            evidence_destination="../secret.json",
        )
