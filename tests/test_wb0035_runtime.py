from __future__ import annotations

import ftplib
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


def _sealed_input() -> FirstWriteUploadInput:
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
        protocol="FTPS_EXPLICIT",
        deploy_identity_scope_reference="evidence:wb0034:scope:ftps",
        authorization_reference=AUTH,
        artifacts=artifacts,
        endpoint_hostname=HOST,
    )


class FakeSock:
    def version(self) -> str:
        return "TLSv1.3"


class FakeFtps:
    def __init__(self) -> None:
        self.sock = FakeSock()
        self.cwd_path = "/"
        self.files: dict[str, dict[str, bytes]] = {"/": {}}
        self.mkd_calls: list[str] = []
        self.stor_calls: list[str] = []
        self.connected_host = ""
        self.protected = False
        self.passive = False

    def connect(self, host: str, port: int, timeout: float | None = None):
        self.connected_host = host
        return "ok"

    def auth(self):
        return "ok"

    def login(self, user: str, passwd: str):
        return "ok"

    def prot_p(self):
        self.protected = True
        return "ok"

    def set_pasv(self, val: bool):
        self.passive = val
        return None

    def pwd(self) -> str:
        return self.cwd_path

    def mlsd(self, path: str = "", facts=None):
        names = set(self.files.get(self.cwd_path, {}))
        prefix = "/" if self.cwd_path == "/" else f"{self.cwd_path}/"
        for candidate in self.files:
            if candidate == self.cwd_path or not candidate.startswith(prefix):
                continue
            remainder = candidate[len(prefix) :]
            if remainder and "/" not in remainder:
                names.add(remainder)
        return iter((name, {}) for name in sorted(names))

    def mkd(self, dirname: str) -> str:
        self.mkd_calls.append(dirname)
        path = f"/{dirname}"
        if path in self.files:
            raise ftplib.error_perm("550 exists")
        self.files[path] = {}
        return path

    def cwd(self, dirname: str):
        path = f"/{dirname}" if self.cwd_path == "/" else f"{self.cwd_path}/{dirname}"
        if path not in self.files:
            raise ftplib.error_perm("550 missing")
        self.cwd_path = path
        return "ok"

    def storbinary(self, cmd: str, fp, blocksize: int = 8192):
        _, name = cmd.split(" ", 1)
        self.stor_calls.append(name)
        self.files[self.cwd_path][name] = fp.read()
        return "ok"

    def retrbinary(self, cmd: str, callback, blocksize: int = 8192):
        _, name = cmd.split(" ", 1)
        callback(self.files[self.cwd_path][name])
        return "ok"

    def quit(self):
        return "ok"

    def close(self):
        return None


class FailingListFtps(FakeFtps):
    def mlsd(self, path: str = "", facts=None):
        raise ftplib.error_perm("550 permission denied")


class PartialStoreFailFtps(FakeFtps):
    def storbinary(self, cmd: str, fp, blocksize: int = 8192):
        _, name = cmd.split(" ", 1)
        self.stor_calls.append(name)
        payload = fp.read()
        self.files[self.cwd_path][name] = payload[:3]
        raise ftplib.error_temp("426 transfer aborted")


def _execute(
    monkeypatch: pytest.MonkeyPatch,
    fake: FakeFtps,
    *,
    upload_input: FirstWriteUploadInput | None = None,
    credential: runtime.FirstWriteFtpsCredential | None = None,
    authorized: bool = True,
    auth_ref: str = AUTH,
):
    upload_input = upload_input or _sealed_input()
    credential = credential or runtime.FirstWriteFtpsCredential(
        HOST, USERNAME, 21, PASSWORD
    )
    monkeypatch.setattr(
        runtime,
        "validate_first_write_packet",
        lambda *_args: FirstWritePacketResult(True, (), upload_input),
    )
    loads = 0

    def loader():
        nonlocal loads
        loads += 1
        return credential

    result = runtime.execute_first_write_ftps(
        Path("manifest"),
        Path("readiness"),
        Path("repo"),
        Path("artifacts"),
        remote_write_authorized=authorized,
        authorization_reference=auth_ref,
        credential_loader=loader,
        ftp_factory=lambda _: fake,
    )
    return result, loads


def test_public_mutating_uploader_is_not_exposed() -> None:
    assert not hasattr(runtime, "upload_first_write_ftps")


def test_capability_cannot_be_constructed_without_guard() -> None:
    with pytest.raises(runtime.FirstWriteRuntimeError, match="capability"):
        runtime._WriteCapability(object(), _sealed_input())


def test_runner_requires_literal_true_and_does_not_load_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, loads = _execute(
        monkeypatch,
        FakeFtps(),
        authorized=cast(bool, "false"),
    )
    assert not result.executed
    assert loads == 0
    assert not result.remote_mutation_possible


def test_runner_false_does_not_load_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    result, loads = _execute(monkeypatch, FakeFtps(), authorized=False)
    assert not result.executed
    assert loads == 0


def test_runner_binds_exact_authorization_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, loads = _execute(monkeypatch, FakeFtps(), auth_ref="approval:wrong")
    assert not result.executed
    assert loads == 0
    assert "authorization reference" in result.errors[0]


def test_bounded_ftps_upload_uses_only_sealed_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    result, loads = _execute(monkeypatch, fake, upload_input=upload_input)

    assert result.executed, result.errors
    assert loads == 1
    assert result.upload_input is upload_input
    destination = f"/cybercore-canary-{RUN_ID}"
    assert fake.mkd_calls == [f"cybercore-canary-{RUN_ID}"]
    assert set(fake.files[destination]) == {"index.html", "cybercore-version.json"}
    assert fake.files[destination]["index.html"] == upload_input.artifact_bytes("index.html")
    assert fake.protected and fake.passive
    assert result.receipt is not None
    assert result.receipt.tls_version == "TLSv1.3"


def test_endpoint_drift_blocks_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(
        "other.example", USERNAME, 21, PASSWORD
    )
    result, _ = _execute(monkeypatch, fake, credential=credential)
    assert not result.executed
    assert fake.connected_host == ""
    assert not result.remote_mutation_possible


def test_username_drift_blocks_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, "eimyherr", 21, PASSWORD)
    result, _ = _execute(monkeypatch, fake, credential=credential)
    assert not result.executed
    assert fake.connected_host == ""
    assert "username" in result.errors[0]


def test_port_drift_blocks_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, USERNAME, 990, PASSWORD)
    result, _ = _execute(monkeypatch, fake, credential=credential)
    assert not result.executed
    assert fake.connected_host == ""
    assert "port 21" in result.errors[0]


def test_existing_destination_blocks_without_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeFtps()
    fake.files[f"/cybercore-canary-{RUN_ID}"] = {}
    result, _ = _execute(monkeypatch, fake)
    assert not result.executed
    assert fake.mkd_calls == []
    assert fake.stor_calls == []
    assert not result.remote_mutation_possible


def test_absence_check_fails_closed_when_parent_listing_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FailingListFtps()
    result, _ = _execute(monkeypatch, fake)
    assert not result.executed
    assert fake.mkd_calls == []
    assert fake.stor_calls == []
    assert not result.remote_mutation_possible


def test_sealed_artifact_digest_drift_blocks_before_connect(
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
    fake = FakeFtps()
    result, _ = _execute(monkeypatch, fake, upload_input=tampered)
    assert not result.executed
    assert fake.connected_host == ""
    assert "digest mismatch" in result.errors[0]


def test_partial_stor_failure_preserves_remote_mutation_state_and_sealed_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    fake = PartialStoreFailFtps()
    result, _ = _execute(monkeypatch, fake, upload_input=upload_input)

    assert not result.executed
    assert result.remote_mutation_possible
    assert result.upload_input is upload_input
    assert result.partial_state is not None
    assert result.partial_state.destination_created
    assert result.partial_state.active_artifact == "cybercore-version.json"
    assert result.partial_state.uploaded_artifacts == ()
    destination = f"/cybercore-canary-{RUN_ID}"
    assert fake.files[destination]["cybercore-version.json"]


def test_partial_state_contains_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = _execute(monkeypatch, PartialStoreFailFtps())
    assert PASSWORD not in repr(result)
    assert result.partial_state is not None
    assert PASSWORD not in repr(result.partial_state)


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
