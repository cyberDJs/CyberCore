from __future__ import annotations

import pytest

from cybercore.execution.server.protocol import RequestValidationError, ServerRequest


def _request(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "version": 1,
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
    assert request.version == 1
    assert request.operation == "vikunja.health.verify"
    assert request.arguments == {}


@pytest.mark.parametrize("version", [0, 2, True, "1"])
def test_protocol_rejects_unsupported_version(version: object) -> None:
    with pytest.raises(RequestValidationError, match="version must equal 1"):
        ServerRequest.from_mapping(_request(version=version))


def test_protocol_rejects_missing_version() -> None:
    request = _request()
    request.pop("version")
    with pytest.raises(RequestValidationError, match="exact protocol schema"):
        ServerRequest.from_mapping(request)


def test_protocol_rejects_extra_field() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(command="id"))


def test_protocol_rejects_free_form_arguments() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(arguments={"path": "/tmp"}))


def test_protocol_rejects_other_target() -> None:
    with pytest.raises(RequestValidationError):
        ServerRequest.from_mapping(_request(target_id="example.org"))
