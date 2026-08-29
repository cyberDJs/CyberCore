from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from cybercore import first_write_runtime as runtime
from cybercore.first_write_effect import STAGING_ORIGIN, verify_first_write_effect
from cybercore.first_write_packet import (
    FirstWritePacketResult,
    FirstWriteUploadInput,
    ValidatedFirstWriteArtifact,
)

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


def _execute(
    monkeypatch: pytest.MonkeyPatch,
    *,
    upload_input: FirstWriteUploadInput | None = None,
    authorized: bool = True,
    auth_ref: str = AUTH,
):
    upload_input = upload_input or _sealed_input()
    monkeypatch.setattr(
        runtime,
        "validate_first_write_packet",
        lambda *_args: FirstWritePacketResult(True, (), upload_input),
    )
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


def test_runner_requires_literal_true_before_atomic_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, loads, factories = _execute(
        monkeypatch,
        authorized=cast(bool, "false"),
    )
    assert not result.executed
    assert "authorization" in result.errors[0]
    assert loads == 0
    assert factories == 0
    assert not result.remote_mutation_possible


def test_runner_binds_exact_authorization_reference_before_atomic_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, loads, factories = _execute(monkeypatch, auth_ref="approval:wrong")
    assert not result.executed
    assert "authorization reference" in result.errors[0]
    assert loads == 0
    assert factories == 0


def test_authorized_first_write_is_fail_closed_before_secret_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    result, loads, factories = _execute(monkeypatch, upload_input=upload_input)

    assert not result.executed
    assert result.upload_input is upload_input
    assert result.errors == (runtime.ATOMIC_NO_OVERWRITE_BLOCKER,)
    assert "atomic no-overwrite" in result.errors[0]
    assert loads == 0
    assert factories == 0
    assert not result.remote_mutation_possible
    assert result.partial_state is None
    assert result.receipt is None
    assert PASSWORD not in repr(result)


def test_protocol_drift_blocks_before_secret_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, loads, factories = _execute(
        monkeypatch,
        upload_input=_sealed_input(protocol="SFTP"),
    )
    assert not result.executed
    assert "FTPS_EXPLICIT" in result.errors[0]
    assert loads == 0
    assert factories == 0


def test_sealed_artifact_digest_drift_blocks_before_atomic_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    bad_artifacts = list(upload_input.artifacts)
    first = bad_artifacts[0]
    bad_artifacts[0] = ValidatedFirstWriteArtifact(first.name, "0" * 64, first.content)
    tampered = FirstWriteUploadInput(
        source_commit=upload_input.source_commit,
        run_id=upload_input.run_id,
        destination=upload_input.destination,
        protocol=upload_input.protocol,
        deploy_identity_scope_reference=upload_input.deploy_identity_scope_reference,
        authorization_reference=upload_input.authorization_reference,
        artifacts=tuple(bad_artifacts),
        endpoint_hostname=upload_input.endpoint_hostname,
    )

    result, loads, factories = _execute(monkeypatch, upload_input=tampered)

    assert not result.executed
    assert "digest mismatch" in result.errors[0]
    assert loads == 0
    assert factories == 0
    assert not result.remote_mutation_possible


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
