from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

if __package__ in {None, ""}:
    from protocol import RequestValidationError, ServerRequest  # type: ignore[import-not-found]
else:
    from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


@dataclass(frozen=True)
class OperationSpec:
    name: str
    argv: tuple[str, ...]
    mutating: bool
    timeout_seconds: int


_OPERATION_SPECS: Mapping[str, OperationSpec] = {
    "vikunja.backup.install": OperationSpec(
        name="vikunja.backup.install",
        argv=(
            "/usr/bin/systemd-run",
            "--unit=cybercore-vikunja-backup-install",
            "--wait",
            "--collect",
            "/usr/local/libexec/cybercore-exec/vikunja-backup-install",
        ),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.run": OperationSpec(
        name="vikunja.backup.run",
        argv=(
            "/usr/bin/systemctl",
            "start",
            "vikunja-backup.service",
        ),
        mutating=True,
        timeout_seconds=120,
    ),
    "vikunja.backup.status": OperationSpec(
        name="vikunja.backup.status",
        argv=("/usr/bin/systemctl", "is-active", "vikunja-backup.timer"),
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
        mutating=False,
        timeout_seconds=15,
    ),
}

SUPPORTED_SERVER_OPERATIONS = frozenset(_OPERATION_SPECS)


def resolve_operation(request: ServerRequest) -> OperationSpec:
    if request.arguments:
        raise RequestValidationError("operation arguments must be empty")
    try:
        return _OPERATION_SPECS[request.operation]
    except KeyError as exc:
        raise RequestValidationError("operation is not supported by the server allowlist") from exc
