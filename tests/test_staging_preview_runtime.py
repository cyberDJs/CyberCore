from __future__ import annotations

import ftplib
import hashlib

from cybercore.first_write_runtime import FirstWriteFtpsCredential
from cybercore import first_write_runtime
from cybercore import staging_preview_runtime as preview

RUN_ID = "20260905T010000Z-eimy34"
AUTH = "approval:eimy-v34-staging:20260905T010000Z-eimy34"
CONTENT = b"<!doctype html><title>EIMY v34</title><!-- unique-preview -->\n"
PASSWORD = "unit-test-only-secret"


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


def test_digest_drift_blocks_before_credentials() -> None:
    original = _input()
    tampered = preview.StagingPreviewUploadInput(
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
