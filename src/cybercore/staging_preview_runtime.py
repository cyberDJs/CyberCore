from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
import ftplib
import hashlib
import io
import re
import ssl
from typing import Protocol, cast
from urllib.parse import quote

from cybercore.first_write_runtime import FirstWriteFtpsCredential, FirstWriteRuntimeError

EXPECTED_ENDPOINT = "staging.eimyherrer.com"
EXPECTED_USERNAME = "ccwb34@eimyherrer.com"
EXPECTED_PORT = 21
EXPECTED_PROTOCOL = "FTPS_EXPLICIT"
MAX_PREVIEW_BYTES = 32 * 1024 * 1024
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{5,95}\Z")
STOU_RESPONSE_PATTERN = re.compile(r"(?:125|150) FILE: (.+)\Z")
FTPS_OPERATION_ERRORS = ftplib.all_errors + (UnicodeDecodeError,)


class _FtpsClient(Protocol):
    sock: object
    last_stou_response: str | None

    def connect(self, host: str, port: int, timeout: float | None = None) -> object: ...
    def auth(self) -> object: ...
    def login(self, user: str, passwd: str) -> object: ...
    def prot_p(self) -> object: ...
    def set_pasv(self, val: bool) -> object: ...
    def pwd(self) -> str: ...
    def mlsd(
        self, path: str = "", facts: list[str] | None = None
    ) -> Iterable[tuple[str, dict[str, str]]]: ...
    def storbinary(self, cmd: str, fp: io.BytesIO, blocksize: int = 8192) -> object: ...
    def retrbinary(
        self, cmd: str, callback: Callable[[bytes], object], blocksize: int = 8192
    ) -> object: ...
    def quit(self) -> object: ...
    def close(self) -> object: ...


class _CapturingFtps(ftplib.FTP_TLS):
    """Capture RFC 1123's preliminary STOU response hidden by ftplib.storbinary()."""

    last_stou_response: str | None = None

    def sendcmd(self, cmd: str) -> str:
        response = super().sendcmd(cmd)
        if cmd.upper().startswith("STOU "):
            self.last_stou_response = response
        return response


FtpsFactory = Callable[[ssl.SSLContext], _FtpsClient]
CredentialLoader = Callable[[], FirstWriteFtpsCredential]


@dataclass(frozen=True)
class StagingPreviewUploadInput:
    run_id: str
    authorization_reference: str
    content: bytes = field(repr=False)
    sha256: str
    endpoint_hostname: str = EXPECTED_ENDPOINT
    protocol: str = EXPECTED_PROTOCOL


@dataclass(frozen=True)
class StagingPreviewReceipt:
    run_id: str
    remote_name: str
    public_url: str
    endpoint_hostname: str
    protocol: str
    tls_version: str
    sha256: str
    byte_length: int
    remote_write_performed: bool = True


@dataclass(frozen=True)
class StagingPreviewExecutionResult:
    executed: bool
    errors: tuple[str, ...]
    receipt: StagingPreviewReceipt | None = None
    upload_input: StagingPreviewUploadInput | None = field(default=None, repr=False)
    remote_mutation_possible: bool = False


def build_staging_preview_input(
    content: bytes,
    *,
    run_id: str,
    authorization_reference: str,
) -> StagingPreviewUploadInput:
    return StagingPreviewUploadInput(
        run_id=run_id,
        authorization_reference=authorization_reference,
        content=bytes(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def validate_staging_preview_input(upload_input: StagingPreviewUploadInput) -> tuple[str, ...]:
    errors: list[str] = []
    if upload_input.protocol != EXPECTED_PROTOCOL:
        errors.append("staging preview runtime requires FTPS_EXPLICIT")
    if upload_input.endpoint_hostname != EXPECTED_ENDPOINT:
        errors.append("staging preview endpoint must remain the approved staging hostname")
    if not RUN_ID_PATTERN.fullmatch(upload_input.run_id):
        errors.append("staging preview run_id is invalid")
    if not upload_input.authorization_reference:
        errors.append("staging preview authorization reference is required")
    if not isinstance(upload_input.content, bytes) or not upload_input.content:
        errors.append("staging preview content must be non-empty immutable bytes")
    elif len(upload_input.content) > MAX_PREVIEW_BYTES:
        errors.append("staging preview content exceeds the bounded size limit")
    if hashlib.sha256(upload_input.content).hexdigest() != upload_input.sha256:
        errors.append("staging preview content digest does not match sealed bytes")
    return tuple(errors)


def _default_ftps_factory(context: ssl.SSLContext) -> _FtpsClient:
    return cast(_FtpsClient, _CapturingFtps(context=context, timeout=15))


def _tls_version(client: _FtpsClient) -> str:
    version = getattr(client.sock, "version", None)
    if not callable(version):
        raise FirstWriteRuntimeError("FTPS control channel did not expose TLS version evidence")
    value = version()
    if not isinstance(value, str) or not value.startswith("TLS"):
        raise FirstWriteRuntimeError("FTPS control channel is not TLS protected")
    return value


def _verify_protected_data_channel(client: _FtpsClient) -> None:
    try:
        next(iter(client.mlsd(facts=["type"])), None)
    except FTPS_OPERATION_ERRORS:
        raise FirstWriteRuntimeError(
            "protected passive FTPS data channel verification failed"
        ) from None


def _parse_stou_name(response: str | None) -> str:
    if response is None:
        raise FirstWriteRuntimeError("STOU server response did not expose the unique pathname")
    match = STOU_RESPONSE_PATTERN.fullmatch(response.strip())
    if match is None:
        raise FirstWriteRuntimeError("STOU server response is not RFC 1123 unique-path evidence")
    remote_name = match.group(1).strip()
    if remote_name.startswith("/"):
        remote_name = remote_name[1:]
    if not remote_name or "/" in remote_name or "\\" in remote_name:
        raise FirstWriteRuntimeError("STOU returned a pathname outside the staging root")
    if remote_name in {".", ".."}:
        raise FirstWriteRuntimeError("STOU returned an unsafe pathname")
    return remote_name


def _hash_remote_file(client: _FtpsClient, name: str) -> str:
    digest = hashlib.sha256()
    try:
        client.retrbinary(f"RETR {name}", digest.update, blocksize=64 * 1024)
    except FTPS_OPERATION_ERRORS:
        raise FirstWriteRuntimeError("cannot verify preview bytes after STOU") from None
    return digest.hexdigest()


def execute_staging_preview_stou(
    upload_input: StagingPreviewUploadInput,
    *,
    remote_write_authorized: bool,
    authorization_reference: str,
    credential_loader: CredentialLoader,
    ftp_factory: FtpsFactory = _default_ftps_factory,
) -> StagingPreviewExecutionResult:
    """Upload one self-contained HTML preview with RFC 959/1123 STOU semantics.

    This is intentionally separate from WB-0034's exact-name two-file canary. That MKD+STOR
    writer remains blocked. STOU requires the server to create a name unique to the current
    directory; RFC 1123 requires the server to return that pathname in the 125/150 response.
    No caller-selected final pathname, overwrite, rename, delete, MKD or CWD operation exists here.
    """

    input_errors = validate_staging_preview_input(upload_input)
    if input_errors:
        return StagingPreviewExecutionResult(False, input_errors, upload_input=upload_input)
    if remote_write_authorized is not True:
        return StagingPreviewExecutionResult(
            False,
            ("fresh staging preview write authorization is required",),
            upload_input=upload_input,
        )
    if authorization_reference != upload_input.authorization_reference:
        return StagingPreviewExecutionResult(
            False,
            ("authorization reference does not match sealed preview input",),
            upload_input=upload_input,
        )

    try:
        credential = credential_loader()
    except FirstWriteRuntimeError as exc:
        return StagingPreviewExecutionResult(False, (str(exc),), upload_input=upload_input)

    if credential.endpoint_hostname != EXPECTED_ENDPOINT:
        return StagingPreviewExecutionResult(
            False,
            ("credential endpoint is not the approved staging endpoint",),
            upload_input=upload_input,
        )
    if credential.username != EXPECTED_USERNAME:
        return StagingPreviewExecutionResult(
            False,
            ("credential username is not the verified staging identity",),
            upload_input=upload_input,
        )
    if credential.port != EXPECTED_PORT:
        return StagingPreviewExecutionResult(
            False,
            ("staging preview FTPS runtime requires port 21",),
            upload_input=upload_input,
        )
    if not credential.password:
        return StagingPreviewExecutionResult(
            False,
            ("staging preview credential is incomplete",),
            upload_input=upload_input,
        )

    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    client = ftp_factory(context)
    write_started = False
    try:
        client.connect(credential.endpoint_hostname, credential.port, timeout=15)
        client.auth()
        client.login(credential.username, credential.password)
        client.prot_p()
        client.set_pasv(True)
        tls_version = _tls_version(client)
        if client.pwd() != "/":
            raise FirstWriteRuntimeError("FTPS identity is not rooted at the approved staging root")
        _verify_protected_data_channel(client)

        prefix = f"eimy-v34-{upload_input.run_id}.html"
        write_started = True
        client.storbinary(
            f"STOU {prefix}",
            io.BytesIO(upload_input.content),
            blocksize=64 * 1024,
        )
        remote_name = _parse_stou_name(client.last_stou_response)
        if _hash_remote_file(client, remote_name) != upload_input.sha256:
            raise FirstWriteRuntimeError("STOU preview hash does not match sealed bytes")

        receipt = StagingPreviewReceipt(
            run_id=upload_input.run_id,
            remote_name=remote_name,
            public_url=f"https://{EXPECTED_ENDPOINT}/{quote(remote_name, safe='-._~')}",
            endpoint_hostname=credential.endpoint_hostname,
            protocol=upload_input.protocol,
            tls_version=tls_version,
            sha256=upload_input.sha256,
            byte_length=len(upload_input.content),
        )
        return StagingPreviewExecutionResult(True, (), receipt, upload_input)
    except FTPS_OPERATION_ERRORS:
        return StagingPreviewExecutionResult(
            False,
            (
                "staging preview FTPS operation failed after STOU started"
                if write_started
                else "staging preview FTPS operation failed before STOU",
            ),
            upload_input=upload_input,
            remote_mutation_possible=write_started,
        )
    except FirstWriteRuntimeError as exc:
        return StagingPreviewExecutionResult(
            False,
            (str(exc),),
            upload_input=upload_input,
            remote_mutation_possible=write_started,
        )
    finally:
        try:
            client.quit()
        except Exception:
            try:
                client.close()
            except Exception:
                pass
