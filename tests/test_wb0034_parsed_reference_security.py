from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.first_write import validate_first_write_readiness
from cybercore.first_write_security import scan_first_write_yaml_text


JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature"
NPM_TOKEN = "npm_abcdefghijklmnopqrstuvwxyz0123456789"
PYPI_TOKEN = "pypi-AgEIcHlwaS5vcmcCJGE5YmNkZWYwMTIzNDU2Nzg5"


@pytest.mark.parametrize(
    "text",
    [
        f"? authorization_reference\n: {JWT}\n",
        f"packet: {{authorization_reference: {NPM_TOKEN}}}\n",
        f"packet:\n  nested: {{effect_verifier_reference: {PYPI_TOKEN}}}\n",
    ],
)
def test_parsed_reference_allowlist_rejects_equivalent_yaml_syntax(text: str) -> None:
    errors = scan_first_write_yaml_text(text, "test packet")

    assert any("non-allowlisted value" in error for error in errors)


@pytest.mark.parametrize(
    "reference",
    [
        f"approval:wb0034:{NPM_TOKEN}",
        f"evidence:wb0034:effect-verifier:{PYPI_TOKEN}",
        f"evidence:wb0034:capability:{JWT}",
    ],
)
def test_approved_reference_prefix_cannot_wrap_a_credential(reference: str) -> None:
    errors = scan_first_write_yaml_text(
        f"authorization_reference: {reference}\n",
        "test packet",
    )

    assert any("non-allowlisted value" in error for error in errors)


def test_parsed_reference_allowlist_accepts_explicit_safe_reference() -> None:
    text = """? authorization_reference
: approval:wb0034:20260824T082600Z
packet: {effect_verifier_reference: evidence:wb0034:effect-verifier:20260824}
"""

    assert scan_first_write_yaml_text(text, "test packet") == ()


def test_parsed_reference_allowlist_accepts_structured_opaque_identifiers() -> None:
    text = """authorization_reference: approval:wb0034:20260827T100500Z-a1b2c3
target_capability_reference: evidence:wb0034:sftp-capability:20260827T100500Z-a1b2c3
deploy_identity_scope_reference: evidence:wb0034:deploy-identity-scope:20260827
"""

    assert scan_first_write_yaml_text(text, "test packet") == ()


def test_readiness_rejects_explicit_key_jwt_reference(tmp_path: Path) -> None:
    template = (
        Path(__file__).resolve().parents[1]
        / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
    )
    text = template.read_text(encoding="utf-8").replace(
        "  authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
        f"  ? authorization_reference\n  : {JWT}",
    )
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(text, encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("non-allowlisted value" in error for error in result.errors)


def test_readiness_rejects_credential_wrapped_in_approved_reference_prefix(
    tmp_path: Path,
) -> None:
    template = (
        Path(__file__).resolve().parents[1]
        / ".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml"
    )
    wrapped = f"approval:wb0034:{NPM_TOKEN}"
    text = template.read_text(encoding="utf-8").replace(
        "authorization_reference: REQUIRED_BEFORE_REMOTE_WRITE",
        f"authorization_reference: {wrapped}",
    )
    readiness = tmp_path / "readiness.yaml"
    readiness.write_text(text, encoding="utf-8")

    result = validate_first_write_readiness(readiness)

    assert not result.schema_ok
    assert any("non-allowlisted value" in error for error in result.errors)
