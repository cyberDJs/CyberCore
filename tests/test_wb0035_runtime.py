from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cybercore import first_write_packet as packet
from cybercore import first_write_runtime as runtime
from cybercore.first_write_effect import STAGING_ORIGIN, verify_first_write_effect
from cybercore.first_write_packet import FirstWriteUploadInput, ValidatedFirstWriteArtifact

RUN_ID = "20260829T003500Z-a1b2c3"
COMMIT = "a" * 40
AUTH = "approval:wb0034:20260829T003500Z-wb0035"
HOST = "staging.eimyherrer.com"
PASSWORD = "unit-test-only-secret"
USERNAME = "ccwb34@eimyherrer.com"


def _sealed_input(*, protocol: str = "FTPS_EXPLICIT") -> FirstWriteUploadInput:
    index = b"<!doctype html><title>CyberCore canary</title>\n"
    marker = (
        json.dumps(
            {
                "repository": "cyberDJs/CyberCore",
                "commit": COMMIT,
                "branch": "main",
                "built_at": "2026-08-29T00:35:00Z",
                "environment": "interserver-shared-hosting-staging",
                "run_id": RUN_ID,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    artifacts = tuple(
        ValidatedFirstWriteArtifact(name, hashlib.sha256(content).hexdigest(), content)
        for name, content in (
            ("cybercore-version.json", marker),
            ("index.html", index),
        )
    )
    return FirstWriteUploadInput(
        source_commit=COMMIT,
        run_id=RUN_ID,
        destination=f"cybercore-canary-{RUN_ID}/",
        protocol=protocol,
        deploy_identity_scope_reference="evidence:wb0034:scope:ftps",
        authorization_reference=AUTH,
        artifacts=artifacts,
        endpoint_hostname=HOST,
    )


def _execute(*, authorized: bool = True, auth_ref: str = AUTH):
    loads = 0
    factories = 0

    def loader():
        nonlocal loads
        loads += 1
        return runtime.FirstWriteFtpsCredential(HOST, USERNAME, 21, PASSWORD)

    def factory(_context):
        nonlocal factories
        factories += 1
        raise AssertionError("FTPS factory must not run while atomic no-overwrite is unproven")

    result = runtime.execute_first_write_ftps(
        Path("manifest"),
        Path("readiness"),
        Path("repo"),
        Path("artifacts"),
        remote_write_authorized=authorized,
        authorization_reference=auth_ref,
        credential_loader=loader,
        ftp_factory=factory,
    )
    return result, loads, factories


def test_module_exposes_no_direct_mutating_uploader_or_capability_token() -> None:
    assert not hasattr(runtime, "upload_first_write_ftps")
    assert not hasattr(runtime, "_upload_first_write_ftps")
    assert not hasattr(runtime, "_WriteCapability")
    assert not hasattr(runtime, "_WRITE_CAPABILITY_GUARD")


def test_first_write_blocker_precedes_packet_validation_and_all_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validations = 0

    def forbidden_validation(*_args, **_kwargs):
        nonlocal validations
        validations += 1
        raise AssertionError("blocked writer must not run packet validation or git fetch")

    monkeypatch.setattr(packet, "validate_first_write_packet", forbidden_validation)

    result, loads, factories = _execute()

    assert not result.executed
    assert result.errors == (runtime.ATOMIC_NO_OVERWRITE_BLOCKER,)
    assert validations == 0
    assert loads == 0
    assert factories == 0
    assert result.upload_input is None
    assert not result.remote_mutation_possible
    assert result.partial_state is None
    assert result.receipt is None
    assert PASSWORD not in repr(result)


def test_first_write_blocker_is_unconditional_for_authority_arguments() -> None:
    result_false, loads_false, factories_false = _execute(authorized=False)
    result_wrong, loads_wrong, factories_wrong = _execute(auth_ref="approval:wrong")

    assert result_false.errors == (runtime.ATOMIC_NO_OVERWRITE_BLOCKER,)
    assert result_wrong.errors == (runtime.ATOMIC_NO_OVERWRITE_BLOCKER,)
    assert loads_false == loads_wrong == 0
    assert factories_false == factories_wrong == 0
    assert not result_false.remote_mutation_possible
    assert not result_wrong.remote_mutation_possible


def test_upload_input_validator_still_rejects_protocol_drift() -> None:
    errors = runtime.validate_first_write_upload_input(_sealed_input(protocol="SFTP"))
    assert any("FTPS_EXPLICIT" in error for error in errors)


def test_upload_input_validator_still_rejects_digest_drift() -> None:
    upload_input = _sealed_input()
    artifacts = list(upload_input.artifacts)
    first = artifacts[0]
    artifacts[0] = ValidatedFirstWriteArtifact(first.name, "0" * 64, first.content)
    tampered = FirstWriteUploadInput(
        source_commit=upload_input.source_commit,
        run_id=upload_input.run_id,
        destination=upload_input.destination,
        protocol=upload_input.protocol,
        deploy_identity_scope_reference=upload_input.deploy_identity_scope_reference,
        authorization_reference=upload_input.authorization_reference,
        artifacts=tuple(artifacts),
        endpoint_hostname=upload_input.endpoint_hostname,
    )

    errors = runtime.validate_first_write_upload_input(tampered)
    assert any("digest mismatch" in error for error in errors)


def test_https_effect_verifier_matches_served_bytes_and_marker() -> None:
    upload_input = _sealed_input()
    bodies = {artifact.name: artifact.content for artifact in upload_input.artifacts}

    def fetcher(url: str):
        name = url.rsplit("/", 1)[-1]
        return 200, url, bodies[name]

    result = verify_first_write_effect(upload_input, fetcher=fetcher)
    assert result.verified, result.errors


def test_https_effect_verifier_rejects_redirect_and_hash_drift() -> None:
    upload_input = _sealed_input()
    bodies = {artifact.name: artifact.content for artifact in upload_input.artifacts}

    def fetcher(url: str):
        name = url.rsplit("/", 1)[-1]
        if name == "index.html":
            return 200, f"{STAGING_ORIGIN}/elsewhere", b"wrong"
        return 200, url, bodies[name]

    result = verify_first_write_effect(upload_input, fetcher=fetcher)
    assert not result.verified
    assert any("redirect" in error for error in result.errors)


def test_keychain_loader_builds_credential_without_exposing_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cybercore import first_write_keychain as keychain

    values = {
        keychain.HOST_SERVICE: HOST,
        keychain.USER_SERVICE: USERNAME,
        keychain.PORT_SERVICE: "21",
        keychain.PASSWORD_SERVICE: PASSWORD,
    }
    monkeypatch.setattr(keychain, "_read_keychain_service", values.__getitem__)
    credential = keychain.load_interserver_staging_ftps_credential()
    assert credential.endpoint_hostname == HOST
    assert credential.port == 21
    assert PASSWORD not in repr(credential)
