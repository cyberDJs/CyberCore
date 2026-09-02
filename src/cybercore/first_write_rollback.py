from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import ssl
from typing import Protocol, cast

from cybercore.first_write_packet import FirstWriteUploadInput
from cybercore.first_write_runtime import (
    EXPECTED_ARTIFACTS,
    EXPECTED_PORT,
    EXPECTED_PROTOCOL,
    EXPECTED_USERNAME,
    FTPS_OPERATION_ERRORS,
    FirstWriteFtpsCredential,
    FirstWriteRuntimeError,
    validate_first_write_upload_input,
)

EXPECTED_ENDPOINT = "staging.eimyherrer.com"
ROLLBACK_AUTH_PREFIX = "approval:wb0036:rollback"


class _RollbackFtpsClient(Protocol):
    sock: object

    def connect(self, host: str, port: int, timeout: float | None = None) -> object: ...
    def auth(self) -> object: ...
    def login(self, user: str, passwd: str) -> object: ...
    def prot_p(self) -> object: ...
    def set_pasv(self, val: bool) -> object: ...
    def pwd(self) -> str: ...
    def sendcmd(self, cmd: str) -> str: ...
    def quit(self) -> object: ...
    def close(self) -> object: ...


RollbackFtpsFactory = Callable[[ssl.SSLContext], _RollbackFtpsClient]
CredentialLoader = Callable[[], FirstWriteFtpsCredential]


@dataclass(frozen=True)
class FirstWriteRollbackReceipt:
    source_commit: str
    run_id: str
    destination: str
    endpoint_hostname: str
    protocol: str
    target_present: bool
    present_artifacts: tuple[str, ...]
    cleanup_required: bool
    already_absent: bool = False
    remote_write_performed: bool = False
    recovery_mode: str = "logical-no-promote"


@dataclass(frozen=True)
class FirstWriteRollbackResult:
    rolled_back: bool
    errors: tuple[str, ...]
    receipt: FirstWriteRollbackReceipt | None = None
    upload_input: FirstWriteUploadInput | None = field(default=None, repr=False)
    remote_mutation_possible: bool = False


def rollback_authorization_reference(upload_input: FirstWriteUploadInput) -> str:
    return f"{ROLLBACK_AUTH_PREFIX}:{upload_input.run_id}:{upload_input.source_commit}"


def _default_ftps_factory(context: ssl.SSLContext) -> _RollbackFtpsClient:
    import ftplib

    return cast(_RollbackFtpsClient, ftplib.FTP_TLS(context=context, timeout=15))


def _tls_version(client: _RollbackFtpsClient) -> str:
    version = getattr(client.sock, "version", None)
    if not callable(version):
        raise FirstWriteRuntimeError("FTPS control channel did not expose TLS version evidence")
    value = version()
    if not isinstance(value, str) or not value.startswith("TLS"):
        raise FirstWriteRuntimeError("FTPS control channel is not TLS protected")
    return value


def _entry_type(facts: dict[str, str]) -> str | None:
    value = facts.get("type")
    return value.lower() if isinstance(value, str) else None


def _probe_exact_path(client: _RollbackFtpsClient, path: str, *, expected_type: str) -> None:
    """Probe exactly one sealed path with MLST; any ambiguity fails closed."""
    try:
        response = client.sendcmd(f"MLST {path}")
    except FTPS_OPERATION_ERRORS:
        raise FirstWriteRuntimeError(
            "cannot prove rollback target metadata over protected FTPS"
        ) from None

    response_lines = response.splitlines()
    if (
        not response_lines
        or not response_lines[0].startswith(("250 ", "250-"))
        or not response_lines[-1].startswith("250 ")
    ):
        raise FirstWriteRuntimeError("MLST did not return a completed 250 reply")

    fact_lines: list[tuple[str, str]] = []
    for raw_line in response_lines:
        line = raw_line[1:] if raw_line.startswith(" ") else raw_line
        facts_text, separator, reported_path = line.partition(" ")
        if separator and "=" in facts_text and ";" in facts_text:
            fact_lines.append((facts_text, reported_path))
    if len(fact_lines) != 1:
        raise FirstWriteRuntimeError("MLST did not return exactly one target metadata record")

    facts_text, reported_path = fact_lines[0]
    facts: dict[str, str] = {}
    for item in facts_text.split(";"):
        if not item:
            continue
        if "=" not in item:
            raise FirstWriteRuntimeError("MLST metadata contains a malformed fact")
        key, value = item.split("=", 1)
        normalized_key = key.lower()
        if not key or normalized_key in facts:
            raise FirstWriteRuntimeError("MLST metadata contains duplicate facts")
        facts[normalized_key] = value

    if reported_path != path:
        raise FirstWriteRuntimeError("MLST metadata record does not match the sealed target path")
    if _entry_type(facts) != expected_type:
        raise FirstWriteRuntimeError(
            f"rollback target is not positively proven to be a {expected_type}"
        )


def execute_first_write_rollback(
    upload_input: FirstWriteUploadInput,
    *,
    rollback_authorized: bool,
    authorization_reference: str,
    credential_loader: CredentialLoader,
    ftp_factory: RollbackFtpsFactory = _default_ftps_factory,
) -> FirstWriteRollbackResult:
    """Read-only logical recovery bounded to three sealed MLST paths."""
    input_errors = validate_first_write_upload_input(upload_input)
    if input_errors:
        return FirstWriteRollbackResult(False, input_errors, upload_input=upload_input)
    if upload_input.protocol != EXPECTED_PROTOCOL:
        return FirstWriteRollbackResult(
            False, ("first-write rollback requires FTPS_EXPLICIT",), upload_input=upload_input
        )
    if upload_input.endpoint_hostname != EXPECTED_ENDPOINT:
        return FirstWriteRollbackResult(
            False,
            ("sealed rollback endpoint is not the approved staging endpoint",),
            upload_input=upload_input,
        )
    if rollback_authorized is not True:
        return FirstWriteRollbackResult(
            False, ("fresh rollback authorization is required",), upload_input=upload_input
        )
    if authorization_reference != rollback_authorization_reference(upload_input):
        return FirstWriteRollbackResult(
            False,
            ("rollback authorization reference does not match sealed run",),
            upload_input=upload_input,
        )

    try:
        credential = credential_loader()
    except FirstWriteRuntimeError as exc:
        return FirstWriteRollbackResult(False, (str(exc),), upload_input=upload_input)

    if credential.endpoint_hostname != EXPECTED_ENDPOINT:
        return FirstWriteRollbackResult(
            False,
            ("credential endpoint is not the approved staging endpoint",),
            upload_input=upload_input,
        )
    if credential.username != EXPECTED_USERNAME:
        return FirstWriteRollbackResult(
            False,
            ("credential username does not match the verified staging identity",),
            upload_input=upload_input,
        )
    if credential.port != EXPECTED_PORT:
        return FirstWriteRollbackResult(
            False,
            ("explicit FTPS first-write rollback requires port 21",),
            upload_input=upload_input,
        )
    if not credential.username or not credential.password:
        return FirstWriteRollbackResult(
            False, ("FTPS credential is incomplete",), upload_input=upload_input
        )

    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    client = ftp_factory(context)
    target_path = f"/{upload_input.destination[:-1]}"
    try:
        client.connect(EXPECTED_ENDPOINT, credential.port, timeout=15)
        client.auth()
        client.login(credential.username, credential.password)
        client.prot_p()
        client.set_pasv(True)
        _tls_version(client)
        if client.pwd() != "/":
            raise FirstWriteRuntimeError("FTPS identity is not rooted at the approved staging root")

        _probe_exact_path(client, target_path, expected_type="dir")
        present: list[str] = []
        for artifact_name in sorted(EXPECTED_ARTIFACTS):
            _probe_exact_path(client, f"{target_path}/{artifact_name}", expected_type="file")
            present.append(artifact_name)

        receipt = FirstWriteRollbackReceipt(
            source_commit=upload_input.source_commit,
            run_id=upload_input.run_id,
            destination=upload_input.destination,
            endpoint_hostname=EXPECTED_ENDPOINT,
            protocol=upload_input.protocol,
            target_present=True,
            present_artifacts=tuple(present),
            cleanup_required=True,
        )
        return FirstWriteRollbackResult(True, (), receipt, upload_input)
    except FirstWriteRuntimeError as exc:
        return FirstWriteRollbackResult(False, (str(exc),), upload_input=upload_input)
    except FTPS_OPERATION_ERRORS:
        return FirstWriteRollbackResult(
            False,
            ("FTPS rollback inspection failed; no remote mutation was attempted",),
            upload_input=upload_input,
        )
    finally:
        try:
            client.quit()
        except Exception:
            try:
                client.close()
            except Exception:
                pass
