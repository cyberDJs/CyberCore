from __future__ import annotations

import subprocess
from typing import Any

import pytest

from cybercore.execution.authorization import ExecutionAuthorizationCheck
from cybercore.execution.server.dispatcher import execute_request
from cybercore.execution.server.nextcloud_operations import (
    NEXTCLOUD_R1_TARGET_ID,
    SUPPORTED_NEXTCLOUD_R1_OPERATIONS,
    resolve_nextcloud_r1_operation,
)
from cybercore.execution.server.protocol import (
    PROTOCOL_VERSION,
    RequestValidationError,
    ServerRequest,
)


class AllowAuthorizationVerifier:
    def verify(self, **kwargs: str) -> ExecutionAuthorizationCheck:
        return ExecutionAuthorizationCheck(True, "test authorization accepted")


def _request(
    operation: str = "nextcloud.r1.offhost.transfer",
    *,
    target_id: str = NEXTCLOUD_R1_TARGET_ID,
) -> ServerRequest:
    return ServerRequest.from_mapping(
        {
            "version": PROTOCOL_VERSION,
            "operation_id": "NC-R1-113",
            "operation": operation,
            "target_id": target_id,
            "plan_id": "#113",
            "plan_revision": "draft-1",
            "authorization_reference": "APPROVE-113",
            "arguments": {},
        },
        expected_target_id=NEXTCLOUD_R1_TARGET_ID,
    )


def test_nextcloud_server_operation_surface_is_exact() -> None:
    assert SUPPORTED_NEXTCLOUD_R1_OPERATIONS == {
        "nextcloud.r1.offhost.transfer",
        "nextcloud.r1.offhost.rollback",
    }


def test_nextcloud_dispatcher_uses_fixed_helper_and_shell_false() -> None:
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=b"{}", stderr=b"")

    receipt = execute_request(
        _request(),
        authorization_verifier=AllowAuthorizationVerifier(),
        runner=runner,
        operation_resolver=resolve_nextcloud_r1_operation,
    )
    assert receipt.status == "EXECUTED"
    assert receipt.mutation_possible is True
    assert calls[0][0] == [
        "/usr/bin/python3",
        "/usr/local/libexec/cybercore-exec/nextcloud-r1-offhost-transfer",
    ]
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["capture_output"] is True


def test_nextcloud_dispatcher_fails_closed_without_authorization() -> None:
    called = False

    def runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    with pytest.raises(RequestValidationError, match="lacks verified authorization"):
        execute_request(
            _request(),
            runner=runner,
            operation_resolver=resolve_nextcloud_r1_operation,
        )
    assert called is False


def test_nextcloud_protocol_rejects_tasks_target_on_nextcloud_server() -> None:
    with pytest.raises(RequestValidationError, match="canonical server target"):
        ServerRequest.from_mapping(
            {
                "version": PROTOCOL_VERSION,
                "operation_id": "NC-R1-113",
                "operation": "nextcloud.r1.offhost.transfer",
                "target_id": "tasks.cyberdjs.org",
                "plan_id": "#113",
                "plan_revision": "draft-1",
                "authorization_reference": "APPROVE-113",
                "arguments": {},
            },
            expected_target_id=NEXTCLOUD_R1_TARGET_ID,
        )


def test_nextcloud_resolver_rejects_unknown_operation() -> None:
    request = _request("nextcloud.r1.offhost.transfer")
    object.__setattr__(request, "operation", "host.shell")
    with pytest.raises(RequestValidationError, match="not supported"):
        resolve_nextcloud_r1_operation(request)
