from __future__ import annotations

import ftplib
import hashlib
import json
from pathlib import Path

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

    def sendcmd(self, cmd: str) -> str:
        _, name = cmd.split(" ", 1)
        if name in self.files.get(self.cwd_path, {}):
            return "250 present"
        directory_path = f"/{name}" if self.cwd_path == "/" else f"{self.cwd_path}/{name}"
        if directory_path in self.files:
            return "250 present"
        raise ftplib.error_perm("550 missing")

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


def test_bounded_ftps_upload_uses_only_sealed_bytes() -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)

    receipt = runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)

    destination = f"/cybercore-canary-{RUN_ID}"
    assert fake.mkd_calls == [f"cybercore-canary-{RUN_ID}"]
    assert set(fake.files[destination]) == {"index.html", "cybercore-version.json"}
    assert fake.files[destination]["index.html"] == upload_input.artifact_bytes("index.html")
    assert fake.protected and fake.passive
    assert receipt.tls_version == "TLSv1.3"
    assert PASSWORD not in repr(credential)


def test_bounded_ftps_upload_rejects_endpoint_drift_before_connect() -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential("other.example", "user", 21, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="endpoint"):
        runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)
    assert fake.connected_host == ""


def test_existing_destination_blocks_without_write() -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    fake.files[f"/cybercore-canary-{RUN_ID}"] = {}
    credential = runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="already exists"):
        runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)
    assert fake.mkd_calls == []
    assert fake.stor_calls == []


def test_runner_does_not_load_secret_without_fresh_write_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    monkeypatch.setattr(
        runtime,
        "validate_first_write_packet",
        lambda *_args: FirstWritePacketResult(True, (), upload_input),
    )
    loaded = False

    def credential_loader():
        nonlocal loaded
        loaded = True
        return runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)

    result = runtime.execute_first_write_ftps(
        Path("manifest"),
        Path("readiness"),
        Path("repo"),
        Path("artifacts"),
        remote_write_authorized=False,
        authorization_reference=AUTH,
        credential_loader=credential_loader,
        ftp_factory=lambda _: FakeFtps(),
    )
    assert not result.executed
    assert not loaded


def test_runner_binds_exact_authorization_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    upload_input = _sealed_input()
    monkeypatch.setattr(
        runtime,
        "validate_first_write_packet",
        lambda *_args: FirstWritePacketResult(True, (), upload_input),
    )
    result = runtime.execute_first_write_ftps(
        Path("manifest"),
        Path("readiness"),
        Path("repo"),
        Path("artifacts"),
        remote_write_authorized=True,
        authorization_reference="approval:wrong",
        credential_loader=lambda: runtime.FirstWriteFtpsCredential(
            HOST, "ccwb34@eimyherrer.com", 21, PASSWORD
        ),
        ftp_factory=lambda _: FakeFtps(),
    )
    assert not result.executed
    assert "authorization reference" in result.errors[0]


def test_https_effect_verifier_matches_served_bytes_and_marker() -> None:
    upload_input = _sealed_input()
    bodies = {artifact.name: artifact.content for artifact in upload_input.artifacts}

    def fetcher(url: str):
        name = url.rsplit("/", 1)[-1]
        return 200, url, bodies[name]

    result = verify_first_write_effect(upload_input, fetcher=fetcher)
    assert result.verified, result.errors
    assert len(result.artifact_sha256) == 2


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
        keychain.USER_SERVICE: "ccwb34@eimyherrer.com",
        keychain.PORT_SERVICE: "21",
        keychain.PASSWORD_SERVICE: PASSWORD,
    }
    monkeypatch.setattr(keychain, "_read_keychain_service", values.__getitem__)
    credential = keychain.load_interserver_staging_ftps_credential()
    assert credential.endpoint_hostname == HOST
    assert credential.port == 21
    assert PASSWORD not in repr(credential)


def test_runner_executes_validated_packet_and_loads_secret_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_input = _sealed_input()
    monkeypatch.setattr(
        runtime,
        "validate_first_write_packet",
        lambda *_args: FirstWritePacketResult(True, (), upload_input),
    )
    fake = FakeFtps()
    loads = 0

    def credential_loader():
        nonlocal loads
        loads += 1
        return runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)

    result = runtime.execute_first_write_ftps(
        Path("manifest"),
        Path("readiness"),
        Path("repo"),
        Path("artifacts"),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=credential_loader,
        ftp_factory=lambda _: fake,
    )
    assert result.executed, result.errors
    assert loads == 1
    assert result.receipt is not None
    assert result.receipt.destination == upload_input.destination
    assert result.upload_input is upload_input


def test_username_drift_blocks_before_connect() -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, "eimyherr", 21, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="username"):
        runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)
    assert fake.connected_host == ""


class FailingListFtps(FakeFtps):
    def mlsd(self, path: str = "", facts=None):
        raise ftplib.error_perm("550 permission denied")


def test_absence_check_fails_closed_when_parent_listing_is_unavailable() -> None:
    upload_input = _sealed_input()
    fake = FailingListFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="data channel verification failed"):
        runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)
    assert fake.mkd_calls == []
    assert fake.stor_calls == []


def test_port_drift_blocks_before_connect() -> None:
    upload_input = _sealed_input()
    fake = FakeFtps()
    credential = runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 990, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="port 21"):
        runtime.upload_first_write_ftps(upload_input, credential, ftp_factory=lambda _: fake)
    assert fake.connected_host == ""


def test_sealed_artifact_digest_drift_blocks_before_connect() -> None:
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
    credential = runtime.FirstWriteFtpsCredential(HOST, "ccwb34@eimyherrer.com", 21, PASSWORD)
    with pytest.raises(runtime.FirstWriteRuntimeError, match="digest mismatch"):
        runtime.upload_first_write_ftps(tampered, credential, ftp_factory=lambda _: fake)
    assert fake.connected_host == ""


def test_https_effect_verifier_rejects_marker_commit_drift() -> None:
    upload_input = _sealed_input()
    bodies = {artifact.name: artifact.content for artifact in upload_input.artifacts}
    marker = json.loads(bodies["cybercore-version.json"])
    marker["commit"] = "b" * 40
    bodies["cybercore-version.json"] = (
        json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()

    def fetcher(url: str):
        name = url.rsplit("/", 1)[-1]
        return 200, url, bodies[name]

    result = verify_first_write_effect(upload_input, fetcher=fetcher)
    assert not result.verified
    assert any("hash" in error or "commit" in error for error in result.errors)
