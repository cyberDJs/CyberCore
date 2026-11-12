from __future__ import annotations

import hashlib
import json
import sys

if __package__ in {None, ""}:
    from dispatcher import (  # type: ignore[import-not-found]
        _blocked,
        _load_request,
        execute_request,
    )
    from nextcloud_operations import (  # type: ignore[import-not-found]
        NEXTCLOUD_R1_TARGET_ID,
        resolve_nextcloud_r1_operation,
    )
    from protocol import (  # type: ignore[import-not-found]
        MAX_REQUEST_BYTES,
        RequestValidationError,
        ServerReceipt,
    )
else:
    from cybercore.execution.server.dispatcher import _blocked, _load_request, execute_request
    from cybercore.execution.server.nextcloud_operations import (
        NEXTCLOUD_R1_TARGET_ID,
        resolve_nextcloud_r1_operation,
    )
    from cybercore.execution.server.protocol import (
        MAX_REQUEST_BYTES,
        RequestValidationError,
        ServerReceipt,
    )


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _public_operation(value: str) -> str:
    if value == "nextcloud.r1.offhost.transfer":
        return "nextcloud.r1.offhost.transfer"
    if value == "nextcloud.r1.offhost.rollback":
        return "nextcloud.r1.offhost.rollback"
    raise RequestValidationError("unexpected operation after governed dispatch")


def _safe_receipt(receipt: ServerReceipt) -> dict[str, object]:
    return {
        "operation_id_sha256": _digest_text(receipt.operation_id),
        "operation": _public_operation(receipt.operation),
        "target_id": NEXTCLOUD_R1_TARGET_ID,
        "plan_id_sha256": _digest_text(receipt.plan_id),
        "plan_revision_sha256": _digest_text(receipt.plan_revision),
        "authorization_reference_sha256": receipt.authorization_reference_sha256,
        "started_at": receipt.started_at,
        "completed_at": receipt.completed_at,
        "exit_code": receipt.exit_code,
        "stdout_sha256": receipt.stdout_sha256,
        "stderr_sha256": receipt.stderr_sha256,
        "status": receipt.status,
        "mutation_possible": receipt.mutation_possible,
        "secret_values_recorded": receipt.secret_values_recorded,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        request = _load_request(raw, expected_target_id=NEXTCLOUD_R1_TARGET_ID)
        receipt = execute_request(
            request,
            operation_resolver=resolve_nextcloud_r1_operation,
        )
        payload = _safe_receipt(receipt)
        exit_code = 0 if receipt.status == "EXECUTED" else 1
    except RequestValidationError:
        payload = _blocked("request validation failed")
        exit_code = 2
    except OSError:
        payload = _blocked("fixed Nextcloud R1 operation executable is unavailable")
        exit_code = 126

    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
