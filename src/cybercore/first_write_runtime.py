from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
import ftplib
import hashlib
import io
from pathlib import Path
import re
import ssl
from typing import Protocol, cast

from cybercore.first_write_packet import (
    FirstWriteUploadInput,
    validate_first_write_packet,
)

EXPECTED_PROTOCOL = "FTPS_EXPLICIT"
EXPECTED_PORT = 21
EXPECTED_USERNAME = "ccwb34@eimyherrer.com"
EXPECTED_ARTIFACTS = {"index.html", "cybercore-version.json"}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{5,95}\Z")


class FirstWriteRuntimeError(RuntimeError):
    """Fail-closed runtime error that never embeds secret material."""


class _FtpsClient(Protocol):
    sock: object

    def connect(self, host: str, port: int, timeout: float | None = None) -> object: ...
    def auth(self) -> object: ...
    def login(self, user: str, passwd: str) -> object: ...
    def prot_p(self) -> object: ...
    def set_pasv(self, val: bool) -> object: ...
    def pwd(self) -> str: ...
    def mlsd(
        self, path: str = "", facts: list[str] | None = None
    ) -> Iterable[tuple[str, dict[str, str]]]: ...
    def sendcmd(self, cmd: str) -> str: ...
    def mkd(self, dirname: str) -> str: ...
    def cwd(self, dirname: str) -> object: ...
    def storbinary(self, cmd: str, fp: io.BytesIO, blocksize: int = 8192) -> object: ...
    def retrbinary(
        self, cmd: str, callback: Callable[[bytes], object], blocksize: int = 8192
    ) -> object: ...
    def quit(self) -> object: ...
    def close(self) -> object: ...


FtpsFactory = Callable[[ssl.SSLContext], _FtpsClient]
CredentialLoader = Callable[[], "FirstWriteFtpsCredential"]


@dataclass(frozen=True)
class FirstWriteFtpsCredential:
    endpoint_hostname: str
    username: str
    port: int
    password: str = field(repr=False)


@dataclass(frozen=True)
class FirstWriteFtpsUploadReceipt:
    source_commit: str
    run_id: str
    destination: str
    endpoint_hostname: str
    protocol: str
    tls_version: str
    artifact_sha256: tuple[tuple[str, str], ...]
    remote_write_performed: bool = True


@dataclass(frozen=True)
class FirstWriteExecutionResult:
    executed: bool
    errors: tuple[str, ...]
    receipt: FirstWriteFtpsUploadReceipt | None = None


def validate_first_write_upload_input(upload_input: FirstWriteUploadInput) -> tuple[str, ...]:
    errors: list[str] = []
    if upload_input.protocol != EXPECTED_PROTOCOL:
        errors.append("first-write runtime requires FTPS_EXPLICIT")
    if not isinstance(upload_input.endpoint_hostname, str) or not upload_input.endpoint_hostname:
        errors.append("FTPS upload input requires endpoint_hostname")
    elif upload_input.endpoint_hostname != upload_input.endpoint_hostname.strip().lower():
        errors.append("FTPS endpoint_hostname must remain canonical lowercase")
    if not RUN_ID_PATTERN.fullmatch(upload_input.run_id):
        errors.append("run_id is not safe for a direct-child canary destination")
    expected_destination = f"cybercore-canary-{upload_input.run_id}/"
    if upload_input.destination != expected_destination:
        errors.append("destination must be the exact approved direct-child canary directory")

    names = [artifact.name for artifact in upload_input.artifacts]
    if set(names) != EXPECTED_ARTIFACTS or len(names) != len(EXPECTED_ARTIFACTS):
        errors.append("sealed upload input must contain exactly the two approved artifacts")
    for artifact in upload_input.artifacts:
        actual = hashlib.sha256(artifact.content).hexdigest()
        if actual != artifact.sha256:
            errors.append(f"sealed artifact digest mismatch: {artifact.name}")
    return tuple(errors)


def _default_ftps_factory(context: ssl.SSLContext) -> _FtpsClient:
    return cast(_FtpsClient, ftplib.FTP_TLS(context=context, timeout=15))


def _tls_version(client: _FtpsClient) -> str:
    version = getattr(client.sock, "version", None)
    if not callable(version):
        raise FirstWriteRuntimeError("FTPS control channel did not expose TLS version evidence")
    value = version()
    if not isinstance(value, str) or not value.startswith("TLS"):
        raise FirstWriteRuntimeError("FTPS control channel is not TLS protected")
    return value


def _assert_missing(client: _FtpsClient, name: str) -> None:
    try:
        client.sendcmd(f"MLST {name}")
    except ftplib.error_perm as exc:
        if str(exc).startswith("550"):
            return
        raise FirstWriteRuntimeError("cannot prove remote path absence") from None
    raise FirstWriteRuntimeError("remote path already exists; no-overwrite gate blocked")


def _hash_remote_file(client: _FtpsClient, name: str) -> str:
    digest = hashlib.sha256()
    try:
        client.retrbinary(f"RETR {name}", digest.update, blocksize=64 * 1024)
    except ftplib.all_errors:
        raise FirstWriteRuntimeError("cannot verify uploaded artifact bytes over FTPS") from None
    return digest.hexdigest()


def upload_first_write_ftps(
    upload_input: FirstWriteUploadInput,
    credential: FirstWriteFtpsCredential,
    *,
    ftp_factory: FtpsFactory = _default_ftps_factory,
) -> FirstWriteFtpsUploadReceipt:
    errors = validate_first_write_upload_input(upload_input)
    if errors:
        raise FirstWriteRuntimeError("; ".join(errors))
    if credential.endpoint_hostname != upload_input.endpoint_hostname:
        raise FirstWriteRuntimeError("credential endpoint does not match sealed FTPS endpoint")
    if credential.username != EXPECTED_USERNAME:
        raise FirstWriteRuntimeError("credential username does not match the verified staging identity")
    if credential.port != EXPECTED_PORT:
        raise FirstWriteRuntimeError("explicit FTPS first-write runtime requires port 21")
    if not credential.username or not credential.password:
        raise FirstWriteRuntimeError("FTPS credential is incomplete")

    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    client = ftp_factory(context)
    destination = upload_input.destination[:-1]
    created_directory = False
    uploaded: list[str] = []
    try:
        client.connect(credential.endpoint_hostname, credential.port, timeout=15)
        client.auth()
        client.login(credential.username, credential.password)
        client.prot_p()
        client.set_pasv(True)
        tls_version = _tls_version(client)
        if client.pwd() != "/":
            raise FirstWriteRuntimeError("FTPS identity is not rooted at the approved staging root")
        try:
            next(iter(client.mlsd()), None)
        except ftplib.all_errors:
            raise FirstWriteRuntimeError(
                "protected passive FTPS data channel verification failed"
            ) from None

        _assert_missing(client, destination)
        try:
            client.mkd(destination)
        except ftplib.all_errors:
            raise FirstWriteRuntimeError("cannot create unique first-write destination") from None
        created_directory = True
        client.cwd(destination)
        if client.pwd().rstrip("/") != f"/{destination}":
            raise FirstWriteRuntimeError("FTPS server did not enter the exact created destination")

        artifacts = sorted(upload_input.artifacts, key=lambda item: item.name)
        for artifact in artifacts:
            _assert_missing(client, artifact.name)
            try:
                client.storbinary(
                    f"STOR {artifact.name}",
                    io.BytesIO(artifact.content),
                    blocksize=64 * 1024,
                )
            except ftplib.all_errors:
                raise FirstWriteRuntimeError("FTPS artifact upload failed") from None
            uploaded.append(artifact.name)
            if _hash_remote_file(client, artifact.name) != artifact.sha256:
                raise FirstWriteRuntimeError("uploaded artifact hash does not match sealed bytes")

        return FirstWriteFtpsUploadReceipt(
            source_commit=upload_input.source_commit,
            run_id=upload_input.run_id,
            destination=upload_input.destination,
            endpoint_hostname=credential.endpoint_hostname,
            protocol=upload_input.protocol,
            tls_version=tls_version,
            artifact_sha256=tuple((artifact.name, artifact.sha256) for artifact in artifacts),
        )
    except FirstWriteRuntimeError:
        raise
    except ftplib.all_errors:
        stage = "after destination creation" if created_directory else "before destination creation"
        count = len(uploaded)
        raise FirstWriteRuntimeError(
            f"FTPS first-write failed {stage}; uploaded artifact count={count}"
        ) from None
    finally:
        try:
            client.quit()
        except Exception:
            try:
                client.close()
            except Exception:
                pass


def execute_first_write_ftps(
    manifest_path: Path,
    readiness_path: Path,
    repository_root: Path,
    artifact_dir: Path,
    *,
    remote_write_authorized: bool,
    authorization_reference: str,
    credential_loader: CredentialLoader,
    ftp_factory: FtpsFactory = _default_ftps_factory,
) -> FirstWriteExecutionResult:
    packet = validate_first_write_packet(
        manifest_path,
        readiness_path,
        repository_root,
        artifact_dir,
    )
    if not packet.ready or packet.upload_input is None:
        return FirstWriteExecutionResult(
            False, tuple(packet.errors) or ("final packet is BLOCKED",)
        )
    upload_input = packet.upload_input
    if not remote_write_authorized:
        return FirstWriteExecutionResult(False, ("fresh remote-write authorization is required",))
    if authorization_reference != upload_input.authorization_reference:
        return FirstWriteExecutionResult(
            False, ("authorization reference does not match sealed packet",)
        )
    if upload_input.protocol != EXPECTED_PROTOCOL:
        return FirstWriteExecutionResult(False, ("sealed packet protocol is not FTPS_EXPLICIT",))

    try:
        credential = credential_loader()
        receipt = upload_first_write_ftps(upload_input, credential, ftp_factory=ftp_factory)
    except FirstWriteRuntimeError as exc:
        return FirstWriteExecutionResult(False, (str(exc),))
    return FirstWriteExecutionResult(True, (), receipt)
