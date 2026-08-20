from __future__ import annotations

from pathlib import Path

from cybercore.staging import (
    validate_manifest,
    validate_remote_write_readiness,
    validate_staging_plan,
    validate_target_contract,
)


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml"
MANIFEST = ROOT / ".cybercore/deploy/manifests/interserver-staging-plan-only.example.yaml"
READINESS = ROOT / ".cybercore/deploy/readiness/interserver-staging-readiness.example.yaml"


def _ready_readiness_text() -> str:
    return (
        READINESS.read_text(encoding="utf-8")
        .replace("staging_url_status: UNKNOWN", "staging_url_status: VERIFIED")
        .replace("staging_path_status: UNKNOWN", "staging_path_status: VERIFIED")
        .replace(
            "production_document_root_excluded: UNKNOWN",
            "production_document_root_excluded: VERIFIED",
        )
        .replace("secret_alias_status: UNKNOWN", "secret_alias_status: VERIFIED")
        .replace("rollback_status: UNKNOWN", "rollback_status: VERIFIED")
        .replace("rollback_tested: false", "rollback_tested: true")
        .replace("effect_verifier_status: UNKNOWN", "effect_verifier_status: VERIFIED")
        .replace(
            "operator_authorization_status: UNKNOWN",
            "operator_authorization_status: APPROVED",
        )
    )


def test_target_contract_is_fail_closed_and_non_secret() -> None:
    result = validate_target_contract(TARGET)

    assert result.ok, result.as_text()


def test_plan_only_manifest_is_valid_without_remote_authorization() -> None:
    result = validate_manifest(MANIFEST)

    assert result.ok, result.as_text()
    assert result.warnings == ("manifest source_commit is not pinned yet",)


def test_staging_plan_validates_target_and_manifest_together() -> None:
    result = validate_staging_plan(TARGET, MANIFEST)

    assert result.ok, result.as_text()


def test_manifest_blocks_staging_apply_without_remote_write_authorization(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                "run_id: bad",
                "repository: cyberDJs/CyberCore",
                "source_branch: main",
                "source_commit: abc123",
                "target_id: interserver-shared-hosting-staging",
                "deploy_mode: staging_apply",
                "rollback_mode: none",
                "effect_verifier: none",
                "operator_authorization_reference: APPROVED",
            ]
        ),
        encoding="utf-8",
    )

    result = validate_manifest(manifest)

    assert not result.ok
    assert any("deploy_mode" in error for error in result.errors)
    assert any("must not claim remote-write authorization" in error for error in result.errors)


def test_target_contract_blocks_plaintext_secret_literals(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    target.write_text(TARGET.read_text(encoding="utf-8") + "\npassword=bad\n", encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("denied literal" in error for error in result.errors)


def test_remote_write_readiness_example_is_fail_closed() -> None:
    result = validate_remote_write_readiness(READINESS)

    assert not result.ok
    assert "live staging remote write remains blocked" in result.warnings
    assert any("staging_url_status" in error for error in result.errors)
    assert any("operator_authorization_status" in error for error in result.errors)


def test_remote_write_readiness_can_be_ready_without_granting_remote_write(
    tmp_path: Path,
) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_ready_readiness_text(), encoding="utf-8")

    result = validate_remote_write_readiness(readiness)

    assert result.ok, result.as_text()
    assert "remote_write_allowed: false" in readiness.read_text(encoding="utf-8")
    assert "production_write_allowed: false" in readiness.read_text(encoding="utf-8")


def test_remote_write_readiness_requires_operator_approval_not_verification(
    tmp_path: Path,
) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace(
            "operator_authorization_status: APPROVED",
            "operator_authorization_status: VERIFIED",
            1,
        ),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("operator_authorization_status: APPROVED" in error for error in result.errors)


def test_remote_write_readiness_requires_verified_target_statuses(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace(
            "staging_url_status: VERIFIED", "staging_url_status: APPROVED", 1
        ),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("staging_url_status: VERIFIED" in error for error in result.errors)


def test_remote_write_readiness_rejects_remote_write_claims(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8")
        .replace("remote_write_requested: false", "remote_write_requested: true")
        .replace("remote_write_allowed: false", "remote_write_allowed: true"),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("remote_write_requested: False" in error for error in result.errors)
    assert any("remote_write_allowed: False" in error for error in result.errors)


def test_remote_write_readiness_rejects_duplicate_remote_write_override(
    tmp_path: Path,
) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text("remote_write_allowed: true\n" + _ready_readiness_text(), encoding="utf-8")

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("duplicate YAML key: remote_write_allowed" in error for error in result.errors)


def test_remote_write_readiness_rejects_plaintext_secret_literals(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        READINESS.read_text(encoding="utf-8") + "\napi_key=bad\n", encoding="utf-8"
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("denied literal" in error for error in result.errors)


def test_remote_write_readiness_rejects_yaml_secret_value_fields(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_ready_readiness_text() + "\npassword: bad\n", encoding="utf-8")

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("denied literal" in error for error in result.errors)


def test_remote_write_readiness_requires_expected_secret_aliases(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace("    - INTERSERVER_STAGING_HOST\n", "", 1),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("INTERSERVER_STAGING_HOST" in error for error in result.errors)


def test_remote_write_readiness_rejects_unexpected_secret_aliases(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace(
            "    - INTERSERVER_STAGING_HOST\n",
            "    - INTERSERVER_STAGING_HOST\n    - hunter2\n",
            1,
        ),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("unexpected required_aliases: hunter2" in error for error in result.errors)


def test_remote_write_readiness_rejects_unexpected_effect_checks(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace(
            "    - receipt_is_stored_without_secrets\n",
            "    - receipt_is_stored_without_secrets\n    - arbitrary_extra_check\n",
            1,
        ),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any(
        "unexpected required_checks: arbitrary_extra_check" in error for error in result.errors
    )


def test_remote_write_readiness_rejects_unknown_top_level_fields(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text() + "\ncredential: hunter2\nproduction_mutation_allowed: true\n",
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any(
        "unexpected keys: credential, production_mutation_allowed" in error
        for error in result.errors
    )


def test_remote_write_readiness_rejects_unknown_nested_fields(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text().replace(
            "  secret_alias_status: VERIFIED\n",
            "  secret_alias_status: VERIFIED\n  credential: hunter2\n",
            1,
        ),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any(
        "secret_alias_readiness contains unexpected keys: credential" in error
        for error in result.errors
    )


def test_remote_write_readiness_rejects_yaml_merge_keys(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        "unsafe: &unsafe\n  remote_write_allowed: true\n<<: *unsafe\n" + _ready_readiness_text(),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("forbids YAML merge key: <<" in error for error in result.errors)


def test_remote_write_readiness_rejects_yaml_merge_tags(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        "!!merge ignored: {remote_write_allowed: true}\n" + _ready_readiness_text(),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("forbids YAML merge tag" in error for error in result.errors)


def test_remote_write_readiness_rejects_free_form_notes(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(_ready_readiness_text() + "\nnotes: hunter2\n", encoding="utf-8")

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any("unexpected keys: notes" in error for error in result.errors)


def test_remote_write_readiness_requires_exact_boolean_types(tmp_path: Path) -> None:
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(
        _ready_readiness_text()
        .replace("remote_write_allowed: false", "remote_write_allowed: 0", 1)
        .replace("safe_secret_aliases_only: true", "safe_secret_aliases_only: 1", 1),
        encoding="utf-8",
    )

    result = validate_remote_write_readiness(readiness)

    assert not result.ok
    assert any(
        "remote_write_allowed: False" in error and "expected bool" in error
        for error in result.errors
    )
    assert any(
        "safe_secret_aliases_only: True" in error and "expected bool" in error
        for error in result.errors
    )
