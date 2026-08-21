from __future__ import annotations

from pathlib import Path

from cybercore.staging import validate_target_contract


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml"
CAPABILITY_CHECK = "verify_deployment_protocol_and_target_capability"


def test_target_contract_requires_capability_check_inside_required_preflight(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.yaml"
    text = TARGET.read_text(encoding="utf-8").replace(
        f"  - {CAPABILITY_CHECK}\n",
        "",
        1,
    )
    text += f"\ndecoy_capability_check: {CAPABILITY_CHECK}\n"
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any(
        f"required_preflight missing checks: {CAPABILITY_CHECK}" in error for error in result.errors
    )


def test_target_contract_rejects_unexpected_required_preflight_check(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    text = TARGET.read_text(encoding="utf-8").replace(
        f"  - {CAPABILITY_CHECK}\n",
        f"  - {CAPABILITY_CHECK}\n  - verify_unapproved_remote_write\n",
        1,
    )
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any(
        "required_preflight contains unexpected checks: verify_unapproved_remote_write" in error
        for error in result.errors
    )


def test_target_contract_rejects_duplicate_required_preflight_check(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    text = TARGET.read_text(encoding="utf-8").replace(
        f"  - {CAPABILITY_CHECK}\n",
        f"  - {CAPABILITY_CHECK}\n  - {CAPABILITY_CHECK}\n",
        1,
    )
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("required_preflight contains duplicate checks" in error for error in result.errors)


def test_target_contract_rejects_duplicate_required_preflight_mapping(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    text = TARGET.read_text(encoding="utf-8").replace(
        "required_preflight:\n",
        "required_preflight:\n  - verify_unapproved_remote_write\nrequired_preflight:\n",
        1,
    )
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("duplicate YAML key: required_preflight" in error for error in result.errors)


def test_target_contract_rejects_yaml_merge_key_for_preflight(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    text = "<<: {required_preflight: [verify_unapproved_remote_write]}\n" + TARGET.read_text(
        encoding="utf-8"
    )
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("forbids YAML merge" in error for error in result.errors)


def test_target_contract_rejects_recursive_yaml_alias_before_structure_walk(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.yaml"
    text = TARGET.read_text(encoding="utf-8") + "\nrecursive: &loop {child: *loop}\n"
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any("target contract forbids YAML anchors" in error for error in result.errors)
    assert any("target contract forbids YAML aliases" in error for error in result.errors)


def test_target_contract_rejects_excessive_anchor_free_yaml_nesting(tmp_path: Path) -> None:
    target = tmp_path / "target.yaml"
    nested_value = "[" * 1200 + "0" + "]" * 1200
    text = TARGET.read_text(encoding="utf-8") + f"\ndeep: {nested_value}\n"
    target.write_text(text, encoding="utf-8")

    result = validate_target_contract(target)

    assert not result.ok
    assert any(
        "target contract exceeds safe YAML nesting depth" in error for error in result.errors
    )
