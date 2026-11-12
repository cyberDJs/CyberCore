from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

if __package__ in {None, ""}:
    from protocol import RequestValidationError, ServerRequest  # type: ignore[import-not-found]
else:
    from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


TASKS_TARGET_ID = "tasks.cyberdjs.org"
NEXTCLOUD_R1_TARGET_ID = "cyberskills-vps-nextcloud-r1"


@dataclass(frozen=True)
class OperationSpec:
    name: str
    target_id: str
    argv: tuple[str, ...]
    mutating: bool
    timeout_seconds: int
    result_kind: str | None = None


_OPERATION_SPECS: Mapping[str, OperationSpec] = {
    "system.inventory": OperationSpec(
        name="system.inventory",
        target_id=TASKS_TARGET_ID,
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/inventory.py",
        ),
        mutating=False,
        timeout_seconds=20,
        result_kind="system_inventory",
    ),
    "vikunja.backup.install": OperationSpec(
        name="vikunja.backup.install",
        target_id=TASKS_TARGET_ID,
        argv=(
            "/usr/bin/systemctl",
            "start",
            "cybercore-vikunja-backup-install.service",
        ),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.run": OperationSpec(
        name="vikunja.backup.run",
        target_id=TASKS_TARGET_ID,
        argv=(
            "/usr/bin/systemctl",
            "start",
            "cybercore-vikunja-backup-run.service",
        ),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.status": OperationSpec(
        name="vikunja.backup.status",
        target_id=TASKS_TARGET_ID,
        argv=("/usr/bin/systemctl", "is-active", "vikunja-backup.timer"),
        mutating=False,
        timeout_seconds=15,
    ),
    "vikunja.health.verify": OperationSpec(
        name="vikunja.health.verify",
        target_id=TASKS_TARGET_ID,
        argv=(
            "/usr/bin/curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "10",
            "http://127.0.0.1:3456/api/v1/info",
        ),
        mutating=False,
        timeout_seconds=15,
    ),
    "nextcloud.r1.offhost.transfer": OperationSpec(
        name="nextcloud.r1.offhost.transfer",
        target_id=NEXTCLOUD_R1_TARGET_ID,
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer",
        ),
        mutating=True,
        timeout_seconds=1800,
    ),
    "nextcloud.r1.offhost.rollback": OperationSpec(
        name="nextcloud.r1.offhost.rollback",
        target_id=NEXTCLOUD_R1_TARGET_ID,
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-rollback",
        ),
        mutating=True,
        timeout_seconds=120,
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
    if request.target_id != spec.target_id:
        raise RequestValidationError("operation target does not match the server allowlist")
    return spec
