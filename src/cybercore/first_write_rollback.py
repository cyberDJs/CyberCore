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

# RFC 3659 section 2.1 character classes used by MLSx facts.
_MLST_RCHAR = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.:!@#$%^&()-_+?/\\'\""
)
_MLST_SCHAR = _MLST_RCHAR | {"="}


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


def _valid_fact_name(value: str) -> bool:
    return bool(value) and all(char in _MLST_RCHAR for char in value)


def _valid_fact_value(value: str) -> bool:
    return all(char in _MLST_SCHAR for char in value)


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
        len(response_lines) != 3
        or not response_lines[0].startswith("250-")
        or not (response_lines[-1] == "250" or response_lines[-1].startswith("250 "))
    ):
        raise FirstWriteRuntimeError("MLST did not return a completed 250 control response")

    raw_metadata = response_lines[1]
    if not raw_metadata.startswith(" ") or raw_metadata.startswith("  "):
        raise FirstWriteRuntimeError("MLST metadata record has invalid protocol indentation")

    entry = raw_metadata[1:]
    facts_text, separator, reported_path = entry.partition(" ")
    if not separator or not facts_text or not reported_path:
        raise FirstWriteRuntimeError("MLST metadata contains a malformed target record")
    if not facts_text.endswith(";"):
        raise FirstWriteRuntimeError("MLST metadata contains malformed fact separators")

    fact_items = facts_text[:-1].split(";")
    if not fact_items or any(not item for item in fact_items):
        raise FirstWriteRuntimeError("MLST metadata contains malformed fact separators")

    facts: dict[str, str] = {}
    for item in fact_items:
        if "=" not in item:
            raise FirstWriteRuntimeError("MLST metadata contains a malformed fact")
        key, value = item.split("=", 1)
        if not _valid_fact_name(key) or not _valid_fact_value(value):
            raise FirstWriteRuntimeError("MLST metadata contains invalid fact characters")
        normalized_key = key.lower()
        if normalized_key in facts:
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
