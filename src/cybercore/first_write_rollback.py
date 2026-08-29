from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
import ftplib
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

ROLLBACK_AUTH_PREFIX = "approval:wb0036:rollback"


class _RollbackFtpsClient(Protocol):
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
    def cwd(self, dirname: str) -> object: ...
    def delete(self, filename: str) -> object: ...
    def rmd(self, dirname: str) -> object: ...
    def quit(self) -> object: ...
    def close(self) -> object: ...


RollbackFtpsFactory = Callable[[ssl.SSLContext], _RollbackFtpsClient]
CredentialLoader = Callable[[], FirstWriteFtpsCredential]


@dataclass(frozen=True)
class FirstWriteRollbackPartialMutation:
    source_commit: str
    run_id: str
    destination: str
    endpoint_hostname: str
    protocol: str
    deleted_artifacts: tuple[str, ...]
    active_artifact: str | None = None
    directory_removal_attempted: bool = False
    directory_removal_uncertain: bool = False


class FirstWriteRollbackMutationError(FirstWriteRuntimeError):
    def __init__(self, message: str, partial_state: FirstWriteRollbackPartialMutation) -> None:
        super().__init__(message)
        self.partial_state = partial_state


@dataclass(frozen=True)
class FirstWriteRollbackReceipt:
    source_commit: str
    run_id: str
    destination: str
    endpoint_hostname: str
    protocol: str
    deleted_artifacts: tuple[str, ...]
    already_absent: bool = False
    remote_write_performed: bool = True


@dataclass(frozen=True)
class FirstWriteRollbackResult:
    rolled_back: bool
    errors: tuple[str, ...]
    receipt: FirstWriteRollbackReceipt | None = None
    upload_input: FirstWriteUploadInput | None = field(default=None, repr=False)
    remote_mutation_possible: bool = False
    partial_state: FirstWriteRollbackPartialMutation | None = None


def rollback_authorization_reference(upload_input: FirstWriteUploadInput) -> str:
    """Return the exact fresh-approval reference required for this run rollback."""

    return f"{ROLLBACK_AUTH_PREFIX}:{upload_input.run_id}:{upload_input.source_commit}"


def _default_ftps_factory(context: ssl.SSLContext) -> _RollbackFtpsClient:
    return cast(_RollbackFtpsClient, ftplib.FTP_TLS(context=context, timeout=15))


def _tls_version(client: _RollbackFtpsClient) -> str:
    version = getattr(client.sock, "version", None)
    if not callable(version):
        raise FirstWriteRuntimeError("FTPS control channel did not expose TLS version evidence")
    value = version()
    if not isinstance(value, str) or not value.startswith("TLS"):
        raise FirstWriteRuntimeError("FTPS control channel is not TLS protected")
    return value


def _list_entries(client: _RollbackFtpsClient) -> list[tuple[str, dict[str, str]]]:
    try:
        return list(client.mlsd())
    except FTPS_OPERATION_ERRORS:
        raise FirstWriteRuntimeError(
            "cannot prove rollback directory contents over protected FTPS"
        ) from None


def _entry_type(facts: dict[str, str]) -> str | None:
    value = facts.get("type")
    return value.lower() if isinstance(value, str) else None


def _validate_parent_target(
    entries: list[tuple[str, dict[str, str]]], destination: str
) -> tuple[bool, tuple[str, ...]]:
    matches = [(name, facts) for name, facts in entries if name == destination]
    if not matches:
        return False, ()
    if len(matches) != 1:
        return True, ("rollback target appears more than once in parent listing",)
    entry_type = _entry_type(matches[0][1])
    if entry_type is not None and entry_type not in {"dir", "cdir", "pdir"}:
        return True, ("rollback target is not a directory",)
    return True, ()


def _validate_target_contents(
    entries: list[tuple[str, dict[str, str]]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    names = [name for name, _facts in entries]
    if len(names) != len(set(names)):
        return (), ("rollback target listing contains duplicate names",)

    unexpected = sorted(set(names) - EXPECTED_ARTIFACTS)
    if unexpected:
        return (), ("rollback target contains unexpected entries",)

    errors: list[str] = []
    for name, facts in entries:
        entry_type = _entry_type(facts)
        if entry_type is not None and entry_type != "file":
            errors.append(f"rollback target entry is not a regular file: {name}")
    if errors:
        return (), tuple(errors)
    return tuple(sorted(names)), ()


def _partial_state(
    upload_input: FirstWriteUploadInput,
    credential: FirstWriteFtpsCredential,
    *,
    deleted_artifacts: list[str],
    active_artifact: str | None,
    directory_removal_attempted: bool,
    directory_removal_uncertain: bool = False,
) -> FirstWriteRollbackPartialMutation:
    return FirstWriteRollbackPartialMutation(
        source_commit=upload_input.source_commit,
        run_id=upload_input.run_id,
        destination=upload_input.destination,
        endpoint_hostname=credential.endpoint_hostname,
        protocol=upload_input.protocol,
        deleted_artifacts=tuple(deleted_artifacts),
        active_artifact=active_artifact,
        directory_removal_attempted=directory_removal_attempted,
        directory_removal_uncertain=directory_removal_uncertain,
    )


def execute_first_write_rollback(
    upload_input: FirstWriteUploadInput,
    *,
    rollback_authorized: bool,
    authorization_reference: str,
    credential_loader: CredentialLoader,
    ftp_factory: RollbackFtpsFactory = _default_ftps_factory,
) -> FirstWriteRollbackResult:
    """Delete only the exact sealed first-write canary directory.

    Missing approved artifacts are allowed because rollback must also recover an interrupted
    upload. Any unexpected entry or non-file target entry blocks deletion.
    """

    input_errors = validate_first_write_upload_input(upload_input)
    if input_errors:
        return FirstWriteRollbackResult(False, input_errors, upload_input=upload_input)
    if upload_input.protocol != EXPECTED_PROTOCOL:
        return FirstWriteRollbackResult(
            False,
            ("first-write rollback requires FTPS_EXPLICIT",),
            upload_input=upload_input,
        )
    if rollback_authorized is not True:
        return FirstWriteRollbackResult(
            False,
            ("fresh rollback authorization is required",),
            upload_input=upload_input,
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

    if credential.endpoint_hostname != upload_input.endpoint_hostname:
        return FirstWriteRollbackResult(
            False,
            ("credential endpoint does not match sealed FTPS endpoint",),
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

    def run_authorized_rollback() -> FirstWriteRollbackReceipt:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        client = ftp_factory(context)
        destination = upload_input.destination[:-1]
        deleted: list[str] = []
        active_artifact: str | None = None
        mutation_attempted = False
        directory_removal_attempted = False
        try:
            client.connect(credential.endpoint_hostname, credential.port, timeout=15)
            client.auth()
            client.login(credential.username, credential.password)
            client.prot_p()
            client.set_pasv(True)
            _tls_version(client)
            if client.pwd() != "/":
                raise FirstWriteRuntimeError(
                    "FTPS identity is not rooted at the approved staging root"
                )

            parent_entries = _list_entries(client)
            exists, parent_errors = _validate_parent_target(parent_entries, destination)
            if parent_errors:
                raise FirstWriteRuntimeError(parent_errors[0])
            if not exists:
                return FirstWriteRollbackReceipt(
                    source_commit=upload_input.source_commit,
                    run_id=upload_input.run_id,
                    destination=upload_input.destination,
                    endpoint_hostname=credential.endpoint_hostname,
                    protocol=upload_input.protocol,
                    deleted_artifacts=(),
                    already_absent=True,
                    remote_write_performed=False,
                )

            client.cwd(destination)
            if client.pwd().rstrip("/") != f"/{destination}":
                raise FirstWriteRuntimeError(
                    "FTPS server did not enter the exact rollback destination"
                )

            contents = _list_entries(client)
            present, content_errors = _validate_target_contents(contents)
            if content_errors:
                raise FirstWriteRuntimeError(content_errors[0])

            for name in present:
                active_artifact = name
                mutation_attempted = True
                client.delete(name)
                deleted.append(name)
                active_artifact = None

            if _list_entries(client):
                raise FirstWriteRuntimeError(
                    "rollback target is not empty after bounded artifact deletion"
                )

            client.cwd("/")
            directory_removal_attempted = True
            mutation_attempted = True
            client.rmd(destination)

            parent_after = _list_entries(client)
            remains, parent_after_errors = _validate_parent_target(parent_after, destination)
            if parent_after_errors:
                raise FirstWriteRuntimeError(parent_after_errors[0])
            if remains:
                raise FirstWriteRuntimeError("rollback target still exists after directory removal")

            return FirstWriteRollbackReceipt(
                source_commit=upload_input.source_commit,
                run_id=upload_input.run_id,
                destination=upload_input.destination,
                endpoint_hostname=credential.endpoint_hostname,
                protocol=upload_input.protocol,
                deleted_artifacts=tuple(deleted),
            )
        except FirstWriteRollbackMutationError:
            raise
        except FirstWriteRuntimeError as exc:
            if mutation_attempted:
                raise FirstWriteRollbackMutationError(
                    str(exc),
                    _partial_state(
                        upload_input,
                        credential,
                        deleted_artifacts=deleted,
                        active_artifact=active_artifact,
                        directory_removal_attempted=directory_removal_attempted,
                    ),
                ) from None
            raise
        except FTPS_OPERATION_ERRORS:
            if mutation_attempted:
                raise FirstWriteRollbackMutationError(
                    "FTPS rollback failed after a bounded delete attempt; remote mutation may be partial",
                    _partial_state(
                        upload_input,
                        credential,
                        deleted_artifacts=deleted,
                        active_artifact=active_artifact,
                        directory_removal_attempted=directory_removal_attempted,
                        directory_removal_uncertain=directory_removal_attempted,
                    ),
                ) from None
            raise FirstWriteRuntimeError("FTPS rollback failed before any delete attempt") from None
        finally:
            try:
                client.quit()
            except Exception:
                try:
                    client.close()
                except Exception:
                    pass

    try:
        receipt = run_authorized_rollback()
    except FirstWriteRollbackMutationError as exc:
        return FirstWriteRollbackResult(
            False,
            (str(exc),),
            upload_input=upload_input,
            remote_mutation_possible=True,
            partial_state=exc.partial_state,
        )
    except FirstWriteRuntimeError as exc:
        return FirstWriteRollbackResult(False, (str(exc),), upload_input=upload_input)
    return FirstWriteRollbackResult(True, (), receipt, upload_input)
