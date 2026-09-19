from __future__ import annotations

import pytest

from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


def _request(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "operation_id": "op-1",
        "operation": "vikunja.health.verify",
        "target_id": "tasks.cyberdjs.org",
        "plan_id": "WB0038",
        "plan_revision": "1",
        "authorization_reference": "grant-1",
        "arguments": {},
    }
    value.update(overrides)
    return value


def test_protocol_accepts_exact_bound_request() -> None:
    request = ServerRequest.from_mapping(_request())
    assert request.operation == "vikunja.health.verify"
    assert request.arguments == {}


def test_protocol_rejects_extra_field() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(command="id"))


def test_protocol_rejects_free_form_arguments() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(arguments={"path": "/tmp"}))


def test_protocol_rejects_other_target() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(target_id="example.org"))
