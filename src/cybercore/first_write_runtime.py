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
class FirstWritePartialMutation:
    source_commit: str
    run_id: str
    destination: str
    endpoint_hostname: str
    protocol: str
    destination_created: bool
    uploaded_artifacts: tuple[str, ...]
    active_artifact: str | None = None
    destination_creation_uncertain: bool = False


class FirstWriteMutationError(FirstWriteRuntimeError):
    def __init__(self, message: str, partial_state: FirstWritePartialMutation) -> None:
        super().__init__(message)
        self.partial_state = partial_state


@dataclass(frozen=True)
class FirstWriteExecutionResult:
    executed: bool
    errors: tuple[str, ...]
    receipt: FirstWriteFtpsUploadReceipt | None = None
    upload_input: FirstWriteUploadInput | None = field(default=None, repr=False)
    remote_mutation_possible: bool = False
    partial_state: FirstWritePartialMutation | None = None


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
        entries = {entry_name for entry_name, _facts in client.mlsd()}
    except ftplib.all_errors:
        raise FirstWriteRuntimeError("cannot prove remote path absence") from None
    if name in entries:
        raise FirstWriteRuntimeError("remote path already exists; no-overwrite gate blocked")


def _hash_remote_file(client: _FtpsClient, name: str) -> str:
    digest = hashlib.sha256()
    try:
        client.retrbinary(f"RETR {name}", digest.update, blocksize=64 * 1024)
    except ftplib.all_errors:
        raise FirstWriteRuntimeError("cannot verify uploaded artifact bytes over FTPS") from None
    return digest.hexdigest()


def _partial_state(
    upload_input: FirstWriteUploadInput,
    credential: FirstWriteFtpsCredential,
    *,
    destination_created: bool,
    uploaded: list[str],
    active_artifact: str | None,
    destination_creation_uncertain: bool = False,
) -> FirstWritePartialMutation:
    return FirstWritePartialMutation(
        source_commit=upload_input.source_commit,
        run_id=upload_input.run_id,
        destination=upload_input.destination,
        endpoint_hostname=credential.endpoint_hostname,
        protocol=upload_input.protocol,
        destination_created=destination_created,
        uploaded_artifacts=tuple(uploaded),
        active_artifact=active_artifact,
        destination_creation_uncertain=destination_creation_uncertain,
    )


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
    if remote_write_authorized is not True:
        return FirstWriteExecutionResult(False, ("fresh remote-write authorization is required",))
    if authorization_reference != upload_input.authorization_reference:
        return FirstWriteExecutionResult(
            False, ("authorization reference does not match sealed packet",)
        )
    if upload_input.protocol != EXPECTED_PROTOCOL:
        return FirstWriteExecutionResult(False, ("sealed packet protocol is not FTPS_EXPLICIT",))

    input_errors = validate_first_write_upload_input(upload_input)
    if input_errors:
        return FirstWriteExecutionResult(False, input_errors, upload_input=upload_input)

    try:
        credential = credential_loader()
    except FirstWriteRuntimeError as exc:
        return FirstWriteExecutionResult(False, (str(exc),), upload_input=upload_input)

    if credential.endpoint_hostname != upload_input.endpoint_hostname:
        return FirstWriteExecutionResult(
            False,
            ("credential endpoint does not match sealed FTPS endpoint",),
            upload_input=upload_input,
        )
    if credential.username != EXPECTED_USERNAME:
        return FirstWriteExecutionResult(
            False,
            ("credential username does not match the verified staging identity",),
            upload_input=upload_input,
        )
    if credential.port != EXPECTED_PORT:
        return FirstWriteExecutionResult(
            False,
            ("explicit FTPS first-write runtime requires port 21",),
            upload_input=upload_input,
        )
    if not credential.username or not credential.password:
        return FirstWriteExecutionResult(
            False, ("FTPS credential is incomplete",), upload_input=upload_input
        )

    def run_authorized_upload() -> FirstWriteFtpsUploadReceipt:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        client = ftp_factory(context)
        destination = upload_input.destination[:-1]
        destination_create_attempted = False
        created_directory = False
        uploaded: list[str] = []
        active_artifact: str | None = None
        try:
            client.connect(credential.endpoint_hostname, credential.port, timeout=15)
            client.auth()
            client.login(credential.username, credential.password)
            client.prot_p()
            client.set_pasv(True)
            tls_version = _tls_version(client)
            if client.pwd() != "/":
                raise FirstWriteRuntimeError(
                    "FTPS identity is not rooted at the approved staging root"
                )
            try:
                next(iter(client.mlsd()), None)
            except ftplib.all_errors:
                raise FirstWriteRuntimeError(
                    "protected passive FTPS data channel verification failed"
                ) from None

            _assert_missing(client, destination)
            destination_create_attempted = True
            client.mkd(destination)
            created_directory = True
            client.cwd(destination)
            if client.pwd().rstrip("/") != f"/{destination}":
                raise FirstWriteRuntimeError(
                    "FTPS server did not enter the exact created destination"
                )

            artifacts = sorted(upload_input.artifacts, key=lambda item: item.name)
            for artifact in artifacts:
                active_artifact = artifact.name
                _assert_missing(client, artifact.name)
                client.storbinary(
                    f"STOR {artifact.name}",
                    io.BytesIO(artifact.content),
                    blocksize=64 * 1024,
                )
                uploaded.append(artifact.name)
                active_artifact = None
                if _hash_remote_file(client, artifact.name) != artifact.sha256:
                    raise FirstWriteRuntimeError(
                        "uploaded artifact hash does not match sealed bytes"
                    )

            return FirstWriteFtpsUploadReceipt(
                source_commit=upload_input.source_commit,
                run_id=upload_input.run_id,
                destination=upload_input.destination,
                endpoint_hostname=credential.endpoint_hostname,
                protocol=upload_input.protocol,
                tls_version=tls_version,
                artifact_sha256=tuple(
                    (artifact.name, artifact.sha256) for artifact in artifacts
                ),
            )
        except FirstWriteMutationError:
            raise
        except FirstWriteRuntimeError as exc:
            if created_directory:
                raise FirstWriteMutationError(
                    str(exc),
                    _partial_state(
                        upload_input,
                        credential,
                        destination_created=True,
                        uploaded=uploaded,
                        active_artifact=active_artifact,
                    ),
                ) from None
            raise
        except ftplib.all_errors:
            if destination_create_attempted:
                state = _partial_state(
                    upload_input,
                    credential,
                    destination_created=created_directory,
                    uploaded=uploaded,
                    active_artifact=active_artifact,
                    destination_creation_uncertain=not created_directory,
                )
                raise FirstWriteMutationError(
                    "FTPS first-write failed after destination creation attempt; remote mutation may be partial",
                    state,
                ) from None
            raise FirstWriteRuntimeError(
                "FTPS first-write failed before destination creation"
            ) from None
        finally:
            try:
                client.quit()
            except Exception:
                try:
                    client.close()
                except Exception:
                    pass

    try:
        receipt = run_authorized_upload()
    except FirstWriteMutationError as exc:
        return FirstWriteExecutionResult(
            False,
            (str(exc),),
            upload_input=upload_input,
            remote_mutation_possible=True,
            partial_state=exc.partial_state,
        )
    except FirstWriteRuntimeError as exc:
        return FirstWriteExecutionResult(False, (str(exc),), upload_input=upload_input)
    return FirstWriteExecutionResult(True, (), receipt, upload_input)
