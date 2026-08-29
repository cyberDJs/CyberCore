from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import ftplib
import hashlib
from pathlib import Path
import re

from cybercore.first_write_packet import (
    FirstWriteUploadInput,
    validate_first_write_packet,
)

EXPECTED_PROTOCOL = "FTPS_EXPLICIT"
EXPECTED_PORT = 21
EXPECTED_USERNAME = "ccwb34@eimyherrer.com"
EXPECTED_ARTIFACTS = {"index.html", "cybercore-version.json"}
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{5,95}\Z")
FTPS_OPERATION_ERRORS = ftplib.all_errors + (UnicodeDecodeError,)
ATOMIC_NO_OVERWRITE_BLOCKER = (
    "FTPS first-write is BLOCKED: MKD plus STOR cannot prove atomic no-overwrite "
    "under concurrent access; a concurrency-safe writer or independently verified "
    "exclusive-access mechanism is required"
)


class FirstWriteRuntimeError(RuntimeError):
    """Fail-closed runtime error that never embeds secret material."""


CredentialLoader = Callable[[], "FirstWriteFtpsCredential"]
FtpsFactory = Callable[[object], object]


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


def execute_first_write_ftps(
    manifest_path: Path,
    readiness_path: Path,
    repository_root: Path,
    artifact_dir: Path,
    *,
    remote_write_authorized: bool,
    authorization_reference: str,
    credential_loader: CredentialLoader,
    ftp_factory: FtpsFactory | None = None,
) -> FirstWriteExecutionResult:
    """Validate the sealed first-write request and fail closed before remote mutation.

    The prior FTPS implementation used an absence check followed by MKD/STOR. FTP STOR
    replaces an existing pathname, so another session could race the check and cause an
    overwrite. Until CyberCore has an atomic create-if-absent writer or independently
    verified exclusive access, this entry point intentionally performs no credential load,
    network connection, directory creation, upload, rename, or delete.

    ``credential_loader`` and ``ftp_factory`` remain in the signature for compatibility with
    the merged WB-0035 call contract; they are deliberately not invoked.
    """

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
        return FirstWriteExecutionResult(
            False,
            ("fresh remote-write authorization is required",),
            upload_input=upload_input,
        )
    if authorization_reference != upload_input.authorization_reference:
        return FirstWriteExecutionResult(
            False,
            ("authorization reference does not match sealed packet",),
            upload_input=upload_input,
        )
    if upload_input.protocol != EXPECTED_PROTOCOL:
        return FirstWriteExecutionResult(
            False,
            ("sealed packet protocol is not FTPS_EXPLICIT",),
            upload_input=upload_input,
        )

    input_errors = validate_first_write_upload_input(upload_input)
    if input_errors:
        return FirstWriteExecutionResult(False, input_errors, upload_input=upload_input)

    # Safety gate from WB-0036 security review. This is intentionally unconditional until
    # a real atomic no-overwrite or independently verified exclusive-access mechanism exists.
    # Do not move credential loading or any network operation above this return.
    return FirstWriteExecutionResult(
        False,
        (ATOMIC_NO_OVERWRITE_BLOCKER,),
        upload_input=upload_input,
        remote_mutation_possible=False,
    )
