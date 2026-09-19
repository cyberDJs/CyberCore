from __future__ import annotations

import hashlib
import subprocess
from typing import Any

import pytest

from cybercore.execution.server.dispatcher import execute_request
from cybercore.execution.server.operations import resolve_operation
from cybercore.execution.server.protocol import (
    PROTOCOL_VERSION,
    RequestValidationError,
    ServerRequest,
)


def _request(operation: str = "vikunja.health.verify") -> ServerRequest:
    return ServerRequest.from_mapping(
        {
            "version": PROTOCOL_VERSION,
            "operation_id": "op-1",
            "operation": operation,
            "target_id": "tasks.cyberdjs.org",
            "plan_id": "WB0038",
            "plan_revision": "1",
            "authorization_reference": "grant-1",
            "arguments": {},
        }
    )


def test_dispatcher_uses_fixed_argv_and_shell_false() -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=b"healthy", stderr=b"")

    receipt = execute_request(_request(), runner=runner)
    assert receipt.status == "EXECUTED"
    assert receipt.mutation_possible is False
    assert calls[0][0][0] == "/usr/bin/curl"
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["capture_output"] is True


def test_receipt_hashes_authorization_reference_instead_of_emitting_it() -> None:
    receipt = execute_request(
        _request(),
        runner=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b""),
    )
    assert receipt.authorization_reference_sha256 == hashlib.sha256(b"grant-1").hexdigest()
    assert not hasattr(receipt, "authorization_reference")
    assert "grant-1" not in str(receipt.as_dict())


def test_unknown_operation_fails_before_execution() -> None:
    request = _request("host.shell")
    with pytest.raises(RequestValidationError):
        resolve_operation(request)


def test_mutating_operation_is_marked_but_not_verified() -> None:
    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    receipt = execute_request(_request("vikunja.backup.run"), runner=runner)
    assert receipt.status == "EXECUTED"
    assert receipt.mutation_possible is True
    assert not hasattr(receipt, "verified")


def test_timeout_emits_failed_receipt_without_raw_output() -> None:
    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(argv, 15, output=b"partial", stderr=b"late")

    receipt = execute_request(_request(), runner=runner)
    assert receipt.status == "FAILED"
    assert receipt.exit_code == 124
    assert receipt.stdout_sha256
    assert receipt.stderr_sha256
    assert not hasattr(receipt, "stdout")
    assert receipt.secret_values_recorded is False
