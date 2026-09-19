from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import ftplib
import hashlib
import json
import stat

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cybercore.first_write_runtime import FirstWriteFtpsCredential, FirstWriteRuntimeError
from cybercore import first_write_runtime
from cybercore import staging_preview_runtime as preview

RUN_ID = "20260905T010000Z-eimy34"
COMMIT = "a" * 40
CONTENT = b"<!doctype html><title>EIMY v34</title><!-- unique-preview -->\n"
CONTENT_SHA256 = hashlib.sha256(CONTENT).hexdigest()
PASSWORD = "unit-test-only-secret"
_PRIVATE_KEY = Ed25519PrivateKey.generate()
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_auth(
    *,
    source_commit: str = COMMIT,
    run_id: str = RUN_ID,
    sha256: str = CONTENT_SHA256,
    byte_length: int = len(CONTENT),
    endpoint_hostname: str = preview.EXPECTED_ENDPOINT,
    protocol: str = preview.EXPECTED_PROTOCOL,
    scope_reference: str = preview.EXPECTED_SCOPE_REFERENCE,
    destination: str = preview.EXPECTED_DESTINATION,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    nonce: str = "unit-test-nonce-0001",
    signing_key: Ed25519PrivateKey = _PRIVATE_KEY,
) -> str:
    issued = issued_at or datetime.now(timezone.utc) - timedelta(seconds=1)
    expires = expires_at or issued + timedelta(minutes=5)
    claims = {
        "version": 1,
        "issuer": preview.AUTH_ISSUER,
        "operation": preview.AUTH_OPERATION,
        "source_commit": source_commit,
        "run_id": run_id,
        "sha256": sha256,
        "byte_length": byte_length,
        "endpoint_hostname": endpoint_hostname,
        "protocol": protocol,
        "scope_reference": scope_reference,
        "destination": destination,
        "rollback_authorized": False,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "nonce": nonce,
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    signature = signing_key.sign(payload)
    return f"{preview.AUTH_TOKEN_PREFIX}{_b64url(payload)}.{_b64url(signature)}"


AUTH = _signed_auth()


@pytest.fixture(autouse=True)
def _trusted_approval_key(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    consumed: set[str] = set()

    def consume(nonce: str, _authorization_reference: str) -> None:
        if nonce in consumed:
            raise FirstWriteRuntimeError(
                "staging preview authorization nonce has already been consumed"
            )
        consumed.add(nonce)

    monkeypatch.setattr(preview, "_load_trusted_approval_public_key", lambda: _PUBLIC_KEY)
    monkeypatch.setattr(preview, "_consume_trusted_authorization_nonce", consume)
    return consumed


class _Sock:
    def version(self) -> str:
        return "TLSv1.3"


class FakeFtps:
    def __init__(
        self,
        *,
        root: str = "/",
        fail_after_store: bool = False,
        malformed_stou_response: bool = False,
        escaped_stou_path: bool = False,
    ) -> None:
        self.sock = _Sock()
        self.root = root
        self.fail_after_store = fail_after_store
        self.malformed_stou_response = malformed_stou_response
        self.escaped_stou_path = escaped_stou_path
        self.last_stou_response: str | None = None
        self.files = {"existing.html": b"do-not-touch"}
        self.types = {"existing.html": "file"}
        self.commands: list[str] = []
        self.connected = False

    def connect(self, host: str, port: int, timeout: float | None = None) -> None:
        self.commands.append(f"CONNECT {host}:{port}")
        self.connected = True

    def auth(self) -> None:
        self.commands.append("AUTH TLS")

    def login(self, user: str, passwd: str) -> None:
        assert passwd == PASSWORD
        self.commands.append(f"LOGIN {user}")

    def prot_p(self) -> None:
        self.commands.append("PROT P")

    def set_pasv(self, val: bool) -> None:
        assert val is True
        self.commands.append("PASV")

    def pwd(self) -> str:
        return self.root

    def mlsd(self, path: str = "", facts: list[str] | None = None):
        assert path == ""
        assert facts == ["type"]
        self.commands.append("MLSD")
        return [(name, {"type": self.types[name]}) for name in sorted(self.files)]

    def storbinary(self, cmd: str, fp, blocksize: int = 8192) -> None:
        assert cmd.startswith("STOU ")
        assert blocksize == 64 * 1024
        self.commands.append(cmd)
        prefix = cmd.removeprefix("STOU ")
        name = f"{prefix}.1"
        self.files[name] = fp.read()
        self.types[name] = "file"
        if self.malformed_stou_response:
            self.last_stou_response = "150 transfer starting without pathname"
        elif self.escaped_stou_path:
            self.last_stou_response = f"150 FILE: ../{name}"
        else:
            self.last_stou_response = f"150 FILE: {name}"
        if self.fail_after_store:
            raise ftplib.error_temp("simulated transport loss")

    def retrbinary(self, cmd: str, callback, blocksize: int = 8192) -> None:
        assert cmd.startswith("RETR ")
        assert blocksize == 64 * 1024
        self.commands.append(cmd)
        callback(self.files[cmd.removeprefix("RETR ")])

    def quit(self) -> None:
        self.commands.append("QUIT")

    def close(self) -> None:
        self.commands.append("CLOSE")


def _input() -> preview.StagingPreviewUploadInput:
    return preview.build_staging_preview_input(
        CONTENT,
        source_commit=COMMIT,
        run_id=RUN_ID,
        authorization_reference=AUTH,
    )


def _credential(
    *,
    host: str = preview.EXPECTED_ENDPOINT,
    user: str = preview.EXPECTED_USERNAME,
    port: int = preview.EXPECTED_PORT,
) -> FirstWriteFtpsCredential:
    return FirstWriteFtpsCredential(host, user, port, PASSWORD)


def test_nonce_socket_allows_root_owned_governed_client_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SocketStat:
        st_mode = stat.S_IFSOCK | 0o660
        st_uid = 0
        st_gid = 4242

    monkeypatch.setattr(preview.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(preview.os, "getegid", lambda: 1000)
    monkeypatch.setattr(preview.os, "getgroups", lambda: [4242])

    socket_stat = SocketStat()
    assert socket_stat.st_mode & stat.S_IWGRP
    assert not socket_stat.st_mode & stat.S_IWOTH
    assert socket_stat.st_gid in set(preview.os.getgroups()) | {preview.os.getegid()}


def test_nonce_socket_rejects_world_writable_or_unassigned_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preview.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(preview.os, "getegid", lambda: 1000)
    monkeypatch.setattr(preview.os, "getgroups", lambda: [2000])

    world_writable_mode = stat.S_IFSOCK | 0o662
    unassigned_group_mode = stat.S_IFSOCK | 0o660

    assert world_writable_mode & stat.S_IWOTH
    assert not unassigned_group_mode & stat.S_IWOTH
    assert 4242 not in set(preview.os.getgroups()) | {preview.os.getegid()}


def test_nonce_service_response_stream_may_arrive_in_multiple_chunks() -> None:
    chunks = [b'{"consumed":', b"true}", b""]

    class SplitResponseSocket:
        def recv(self, _size: int) -> bytes:
            return chunks.pop(0)

    client = SplitResponseSocket()
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = client.recv(min(1024, 4097 - total))
        if not chunk:
            break
        parts.append(chunk)
        total += len(chunk)
        assert total <= 4096

    assert b"".join(parts) == b'{"consumed":true}'


def test_capturing_ftps_records_rfc1123_stou_response(monkeypatch) -> None:
    monkeypatch.setattr(
        ftplib.FTP_TLS,
        "sendcmd",
        lambda _self, _cmd: "150 FILE: eimy-v34-generated.html",
    )
    client = preview._CapturingFtps()
    response = client.sendcmd("STOU requested.html")
    assert response == "150 FILE: eimy-v34-generated.html"
    assert client.last_stou_response == response


def test_stou_preview_is_single_file_no_overwrite_and_hash_verified() -> None:
    fake = FakeFtps()
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )

    assert result.executed, result.errors
    assert result.receipt is not None
    assert result.receipt.remote_name == f"eimy-v34-{RUN_ID}.html.1"
    assert result.receipt.sha256 == hashlib.sha256(CONTENT).hexdigest()
    assert result.receipt.public_url.endswith(result.receipt.remote_name)
    assert fake.files["existing.html"] == b"do-not-touch"
    mutations = [cmd for cmd in fake.commands if cmd.startswith(("STOU ", "STOR ", "MKD ", "RN"))]
    assert mutations == [f"STOU eimy-v34-{RUN_ID}.html"]
    assert not result.remote_mutation_possible
    assert PASSWORD not in repr(result)


def test_authorization_blocks_before_credentials_and_factory() -> None:
    calls = {"loader": 0, "factory": 0}

    def loader() -> FirstWriteFtpsCredential:
        calls["loader"] += 1
        return _credential()

    def factory(_context):
        calls["factory"] += 1
        return FakeFtps()

    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=False,
        authorization_reference=AUTH,
        credential_loader=loader,
        ftp_factory=factory,
    )
    mismatch = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference="approval:wrong",
        credential_loader=loader,
        ftp_factory=factory,
    )

    assert not result.executed
    assert not mismatch.executed
    assert calls == {"loader": 0, "factory": 0}


def test_signed_authorization_binds_full_operation_before_credentials() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    cases = (
        ("run_id", _signed_auth(run_id=RUN_ID + "-other")),
        ("sha256", _signed_auth(sha256="0" * 64)),
        ("source_commit", _signed_auth(source_commit="b" * 40)),
        ("scope_reference", _signed_auth(scope_reference="evidence:wrong")),
        ("destination", _signed_auth(destination="somewhere-else")),
    )
    for expected_claim, authorization in cases:
        original = _input()
        candidate = preview.StagingPreviewUploadInput(
            source_commit=original.source_commit,
            run_id=original.run_id,
            authorization_reference=authorization,
            content=original.content,
            sha256=original.sha256,
            endpoint_hostname=original.endpoint_hostname,
            protocol=original.protocol,
            deploy_identity_scope_reference=original.deploy_identity_scope_reference,
            destination=original.destination,
        )
        result = preview.execute_staging_preview_stou(
            candidate,
            remote_write_authorized=True,
            authorization_reference=authorization,
            credential_loader=loader,
        )
        assert not result.executed
        assert any(f"does not bind {expected_claim}" in error for error in result.errors)

    assert loads == 0


def test_reproducible_legacy_reference_is_not_authorization_evidence() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    old_reference = f"approval:eimy-v34-staging:{RUN_ID}:sha256:{CONTENT_SHA256}"
    candidate = preview.build_staging_preview_input(
        CONTENT,
        source_commit=COMMIT,
        run_id=RUN_ID,
        authorization_reference=old_reference,
    )
    result = preview.execute_staging_preview_stou(
        candidate,
        remote_write_authorized=True,
        authorization_reference=old_reference,
        credential_loader=loader,
    )

    assert not result.executed
    assert any("trusted signed approval" in error for error in result.errors)
    assert loads == 0


def test_approval_signed_by_untrusted_key_blocks_before_credentials() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    forged = _signed_auth(signing_key=Ed25519PrivateKey.generate())
    candidate = preview.build_staging_preview_input(
        CONTENT,
        source_commit=COMMIT,
        run_id=RUN_ID,
        authorization_reference=forged,
    )
    result = preview.execute_staging_preview_stou(
        candidate,
        remote_write_authorized=True,
        authorization_reference=forged,
        credential_loader=loader,
    )

    assert not result.executed
    assert result.errors == ("staging preview authorization signature is invalid",)
    assert loads == 0


def test_missing_trusted_approval_key_blocks_before_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    def unavailable():
        raise FirstWriteRuntimeError("trusted staging approval public key is unavailable")

    monkeypatch.setattr(preview, "_load_trusted_approval_public_key", unavailable)
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=loader,
    )
    assert not result.executed
    assert result.errors == ("trusted staging approval public key is unavailable",)
    assert loads == 0


def test_digest_drift_blocks_before_credentials() -> None:
    original = _input()
    tampered = preview.StagingPreviewUploadInput(
        source_commit=original.source_commit,
        run_id=original.run_id,
        authorization_reference=original.authorization_reference,
        content=original.content + b"tampered",
        sha256=original.sha256,
    )
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    result = preview.execute_staging_preview_stou(
        tampered,
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=loader,
    )
    assert not result.executed
    assert any("digest" in error for error in result.errors)
    assert loads == 0


def test_credential_scope_drift_blocks_before_ftps_factory() -> None:
    factories = 0

    def factory(_context):
        nonlocal factories
        factories += 1
        return FakeFtps()

    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=lambda: _credential(user="wrong@example.invalid"),
        ftp_factory=factory,
    )
    assert not result.executed
    assert factories == 0


def test_non_root_identity_blocks_before_stou() -> None:
    fake = FakeFtps(root="/unexpected")
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )
    assert not result.executed
    assert not any(cmd.startswith("STOU ") for cmd in fake.commands)
    assert not result.remote_mutation_possible


def test_malformed_stou_path_evidence_fails_closed_without_overwrite() -> None:
    fake = FakeFtps(malformed_stou_response=True)
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )
    assert not result.executed
    assert result.remote_mutation_possible
    assert any("RFC 1123" in error for error in result.errors)
    assert fake.files["existing.html"] == b"do-not-touch"


def test_stou_path_escape_is_rejected_after_safe_unique_write() -> None:
    fake = FakeFtps(escaped_stou_path=True)
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )
    assert not result.executed
    assert result.remote_mutation_possible
    assert any("outside the staging root" in error for error in result.errors)


def test_transport_loss_after_stou_is_conservatively_mutation_possible() -> None:
    fake = FakeFtps(fail_after_store=True)
    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )
    assert not result.executed
    assert result.remote_mutation_possible
    assert PASSWORD not in repr(result)


def test_same_signed_approval_cannot_reach_stou_twice(
    _trusted_approval_key: set[str],
) -> None:
    fake = FakeFtps()
    first = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )
    second = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )

    assert first.executed
    assert not second.executed
    assert second.errors == ("staging preview authorization nonce has already been consumed",)
    assert len([command for command in fake.commands if command.startswith("STOU ")]) == 1
    assert _trusted_approval_key == {"unit-test-nonce-0001"}


def test_non_string_identifiers_fail_closed_before_credentials() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    original = _input()
    cases = (
        preview.StagingPreviewUploadInput(
            source_commit=None,  # type: ignore[arg-type]
            run_id=original.run_id,
            authorization_reference=original.authorization_reference,
            content=original.content,
            sha256=original.sha256,
        ),
        preview.StagingPreviewUploadInput(
            source_commit=original.source_commit,
            run_id=None,  # type: ignore[arg-type]
            authorization_reference=original.authorization_reference,
            content=original.content,
            sha256=original.sha256,
        ),
    )

    for candidate in cases:
        result = preview.execute_staging_preview_stou(
            candidate,
            remote_write_authorized=True,
            authorization_reference=AUTH,
            credential_loader=loader,
        )
        assert not result.executed
        assert any(
            "source_commit is invalid" in error or "run_id is invalid" in error
            for error in result.errors
        )

    assert loads == 0


def test_authorization_expiry_is_revalidated_immediately_before_nonce_consumption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    consumed = 0
    fake = FakeFtps()
    real_verify = preview._verify_authorization_evidence

    def verify(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_verify(*args, **kwargs)
        return "staging preview authorization has expired"

    def consume(_nonce: str, _authorization_reference: str) -> None:
        nonlocal consumed
        consumed += 1

    monkeypatch.setattr(preview, "_verify_authorization_evidence", verify)
    monkeypatch.setattr(preview, "_consume_trusted_authorization_nonce", consume)

    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )

    assert not result.executed
    assert result.errors == ("staging preview authorization has expired",)
    assert calls == 2
    assert consumed == 0
    assert not any(command.startswith("STOU ") for command in fake.commands)
    assert not result.remote_mutation_possible


def test_authorization_expiry_after_nonce_consumption_blocks_stou(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    consumed = 0
    fake = FakeFtps()
    real_verify = preview._verify_authorization_evidence

    def verify(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            return real_verify(*args, **kwargs)
        return "staging preview authorization has expired"

    def consume(_nonce: str, _authorization_reference: str) -> None:
        nonlocal consumed
        consumed += 1

    monkeypatch.setattr(preview, "_verify_authorization_evidence", verify)
    monkeypatch.setattr(preview, "_consume_trusted_authorization_nonce", consume)

    result = preview.execute_staging_preview_stou(
        _input(),
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=_credential,
        ftp_factory=lambda _context: fake,
    )

    assert not result.executed
    assert result.errors == ("staging preview authorization has expired",)
    assert calls == 3
    assert consumed == 1
    assert not any(command.startswith("STOU ") for command in fake.commands)
    assert not result.remote_mutation_possible


def test_non_string_sha256_fails_closed_without_hashing_or_credentials() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    candidate = preview.StagingPreviewUploadInput(
        source_commit=COMMIT,
        run_id=RUN_ID,
        authorization_reference=AUTH,
        content=CONTENT,
        sha256=None,  # type: ignore[arg-type]
    )
    result = preview.execute_staging_preview_stou(
        candidate,
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=loader,
    )

    assert not result.executed
    assert result.errors == ("staging preview sha256 is invalid",)
    assert loads == 0


def test_non_bytes_content_fails_closed_without_hashing_or_credentials() -> None:
    loads = 0

    def loader() -> FirstWriteFtpsCredential:
        nonlocal loads
        loads += 1
        return _credential()

    candidate = preview.StagingPreviewUploadInput(
        source_commit=COMMIT,
        run_id=RUN_ID,
        authorization_reference=AUTH,
        content="not-bytes",  # type: ignore[arg-type]
        sha256=CONTENT_SHA256,
    )
    result = preview.execute_staging_preview_stou(
        candidate,
        remote_write_authorized=True,
        authorization_reference=AUTH,
        credential_loader=loader,
    )

    assert not result.executed
    assert result.errors == ("staging preview content must be non-empty immutable bytes",)
    assert loads == 0


def test_legacy_two_file_first_write_remains_hard_blocked() -> None:
    result = first_write_runtime.execute_first_write_ftps(
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        remote_write_authorized=True,
        authorization_reference="irrelevant",
        credential_loader=_credential,
    )
    assert not result.executed
    assert result.errors == (first_write_runtime.ATOMIC_NO_OVERWRITE_BLOCKER,)
