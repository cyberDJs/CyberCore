from __future__ import annotations

from typing import Mapping

if __package__ in {None, ""}:
    from operations import OperationSpec  # type: ignore[import-not-found]
    from protocol import RequestValidationError, ServerRequest  # type: ignore[import-not-found]
else:
    from cybercore.execution.server.operations import OperationSpec
    from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


NEXTCLOUD_R1_TARGET_ID = "cyberskills-vps-nextcloud-r1"

_OPERATION_SPECS: Mapping[str, OperationSpec] = {
    "nextcloud.r1.offhost.transfer": OperationSpec(
        name="nextcloud.r1.offhost.transfer",
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer",
        ),
        mutating=True,
        timeout_seconds=3300,
    ),
    "nextcloud.r1.offhost.rollback": OperationSpec(
        name="nextcloud.r1.offhost.rollback",
        argv=(
            "/usr/bin/python3",
            "/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-rollback",
        ),
        mutating=True,
        timeout_seconds=120,
    ),
}

SUPPORTED_NEXTCLOUD_R1_OPERATIONS = frozenset(_OPERATION_SPECS)
MAX_NEXTCLOUD_R1_OPERATION_TIMEOUT_SECONDS = max(
    spec.timeout_seconds for spec in _OPERATION_SPECS.values()
)


def resolve_nextcloud_r1_operation(request: ServerRequest) -> OperationSpec:
    if request.target_id != NEXTCLOUD_R1_TARGET_ID:
        raise RequestValidationError("request target is not the Nextcloud R1 server target")
    if request.arguments:
        raise RequestValidationError("operation arguments must be empty")
    try:
        return _OPERATION_SPECS[request.operation]
    except KeyError as exc:
        raise RequestValidationError(
            "operation is not supported by the Nextcloud R1 server allowlist"
        ) from exc
