from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

if __package__ in {None, ""}:
    from protocol import RequestValidationError, ServerRequest  # type: ignore[import-not-found]
else:
    from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


TASKS_TARGET_ID = "tasks.cyberdjs.org"
NEXTCLOUD_R1_TARGET_ID = "cyberskills-vps"


@dataclass(frozen=True)
class OperationSpec:
    name: str
    argv: tuple[str, ...]
    target_ids: frozenset[str]
    mutating: bool
    timeout_seconds: int
    result_kind: str | None = None


_OPERATION_SPECS: Mapping[str, OperationSpec] = {
    "system.inventory": OperationSpec(
        name="system.inventory",
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/inventory.py",
        ),
        target_ids=frozenset({TASKS_TARGET_ID}),
        mutating=False,
        timeout_seconds=20,
        result_kind="system_inventory",
    ),
    "vikunja.backup.install": OperationSpec(
        name="vikunja.backup.install",
        argv=(
            "/usr/bin/systemctl",
            "start",
            "cybercore-vikunja-backup-install.service",
        ),
        target_ids=frozenset({TASKS_TARGET_ID}),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.run": OperationSpec(
        name="vikunja.backup.run",
        argv=(
            "/usr/bin/systemctl",
            "start",
            "cybercore-vikunja-backup-run.service",
        ),
        target_ids=frozenset({TASKS_TARGET_ID}),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.status": OperationSpec(
        name="vikunja.backup.status",
        argv=("/usr/bin/systemctl", "is-active", "vikunja-backup.timer"),
        target_ids=frozenset({TASKS_TARGET_ID}),
        mutating=False,
        timeout_seconds=15,
    ),
    "vikunja.health.verify": OperationSpec(
        name="vikunja.health.verify",
        argv=(
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "10",
            "http://127.0.0.1:3456/api/v1/info",
        ),
        target_ids=frozenset({TASKS_TARGET_ID}),
        mutating=False,
        timeout_seconds=15,
    ),
    "nextcloud.r1.offhost.transfer": OperationSpec(
        name="nextcloud.r1.offhost.transfer",
        argv=(
            "/usr/bin/systemctl",
            "start",
            "--no-block",
            "cybercore-nextcloud-r1-transfer.service",
        ),
        target_ids=frozenset({NEXTCLOUD_R1_TARGET_ID}),
        mutating=True,
        timeout_seconds=15,
    ),
    "nextcloud.r1.offhost.rollback": OperationSpec(
        name="nextcloud.r1.offhost.rollback",
        argv=(
            "/usr/bin/systemctl",
            "start",
            "cybercore-nextcloud-r1-rollback.service",
        ),
        target_ids=frozenset({NEXTCLOUD_R1_TARGET_ID}),
        mutating=True,
        timeout_seconds=60,
    ),
    "nextcloud.r1.offhost.status": OperationSpec(
        name="nextcloud.r1.offhost.status",
        argv=(
            "/usr/bin/systemctl",
            "is-active",
            "cybercore-nextcloud-r1-transfer.service",
        ),
        target_ids=frozenset({NEXTCLOUD_R1_TARGET_ID}),
        mutating=False,
        timeout_seconds=15,
    ),
    "nextcloud.r1.offhost.verify": OperationSpec(
        name="nextcloud.r1.offhost.verify",
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec-nextcloud-r1/verify.py",
        ),
        target_ids=frozenset({NEXTCLOUD_R1_TARGET_ID}),
        mutating=False,
        timeout_seconds=300,
    ),
}

SUPPORTED_SERVER_OPERATIONS = frozenset(_OPERATION_SPECS)
MAX_SERVER_OPERATION_TIMEOUT_SECONDS = max(
    spec.timeout_seconds for spec in _OPERATION_SPECS.values()
)


def resolve_operation(request: ServerRequest) -> OperationSpec:
    if request.arguments:
        raise RequestValidationError("operation arguments must be empty")
    try:
        spec = _OPERATION_SPECS[request.operation]
    except KeyError as exc:
        raise RequestValidationError("operation is not supported by the server allowlist") from exc
    if request.target_id not in spec.target_ids:
        raise RequestValidationError("operation is not allowed for this server target")
    return spec
