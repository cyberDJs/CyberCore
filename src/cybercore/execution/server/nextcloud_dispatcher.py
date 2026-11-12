from __future__ import annotations

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
    from protocol import MAX_REQUEST_BYTES, RequestValidationError  # type: ignore[import-not-found]
else:
    from cybercore.execution.server.dispatcher import _blocked, _load_request, execute_request
    from cybercore.execution.server.nextcloud_operations import (
        NEXTCLOUD_R1_TARGET_ID,
        resolve_nextcloud_r1_operation,
    )
    from cybercore.execution.server.protocol import MAX_REQUEST_BYTES, RequestValidationError


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    try:
        request = _load_request(raw, expected_target_id=NEXTCLOUD_R1_TARGET_ID)
        payload = execute_request(
            request,
            operation_resolver=resolve_nextcloud_r1_operation,
        ).as_dict()
        exit_code = 0 if payload["status"] == "EXECUTED" else 1
    except RequestValidationError as exc:
        payload = _blocked(str(exc))
        exit_code = 2
    except OSError:
        payload = _blocked("fixed Nextcloud R1 operation executable is unavailable")
        exit_code = 126

    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
