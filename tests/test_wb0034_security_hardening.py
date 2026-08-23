from __future__ import annotations

from pathlib import Path

import pytest

from cybercore import first_write_evidence as evidence_module
from cybercore.first_write_evidence import validate_first_write_evidence
from cybercore.first_write_security import scan_first_write_yaml_text


@pytest.mark.parametrize(
    "value",
    [
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature",
        "npm_abcdefghijklmnopqrstuvwxyz0123456789",
        "pypi-AgEIcHlwaS5vcmcCJGE5YmNkZWYwMTIzNDU2Nzg5",
        "AKIAIOSFODNN7EXAMPLE",
    ],
)
def test_reference_fields_reject_bearer_or_credential_literals(value: str) -> None:
    errors = scan_first_write_yaml_text(
        f"authorization_reference: {value}\n",
        "test packet",
    )

    assert any("non-allowlisted value" in error for error in errors)


def test_reference_fields_accept_only_expected_wb0034_reference_forms() -> None:
    text = """target_capability_reference: evidence:wb0034:sftp-capability:20260823
deploy_identity_scope_reference: evidence:wb0034:deploy-identity-scope:20260823
effect_verifier_reference: evidence:wb0034:effect-verifier:20260823
authorization_reference: approval:wb0034:20260823T164800Z
evidence_bundle_reference: ../evidence/wb0034-first-write.yaml
source_commit_reference: 0123456789abcdef0123456789abcdef01234567
operator_authorization_reference: NOT_REQUIRED_FOR_PLAN_ONLY
"""

    assert scan_first_write_yaml_text(text, "test packet") == ()


def test_evidence_yaml_excessive_nesting_fails_closed(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.yaml"
    nested = "value: 1\n"
    for index in reversed(range(70)):
        nested = (
            f"level_{index}:\n"
            + "\n".join(f"  {line}" if line else line for line in nested.splitlines())
            + "\n"
        )
    evidence.write_text(nested, encoding="utf-8")

    result = validate_first_write_evidence(evidence)

    assert not result.ok
    assert any("safe YAML nesting depth" in error for error in result.errors)


def test_evidence_yaml_recursion_error_is_returned_as_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.yaml"
    evidence.write_text("version: 1\n", encoding="utf-8")

    def raise_recursion(*args: object, **kwargs: object) -> object:
        raise RecursionError("synthetic recursion limit")

    monkeypatch.setattr(evidence_module.yaml, "load", raise_recursion)

    result = validate_first_write_evidence(evidence)

    assert not result.ok
    assert any("invalid YAML" in error for error in result.errors)
