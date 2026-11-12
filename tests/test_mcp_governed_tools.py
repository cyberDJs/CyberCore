from __future__ import annotations

from cybercore.execution.models import ExecutionReceipt, ExecutionStatus
import cybercore.mcp.governed_tools as governed_tools


class DummyVerifier:
    def verify(self, **kwargs):
        raise AssertionError("fake execute_action should own verifier invocation in this unit test")


def test_governed_handler_builds_only_fixed_nextcloud_r1_action(monkeypatch) -> None:
    observed = {}

    def fake_execute(action, target, *, authorization_verifier):
        observed["action"] = action
        observed["target"] = target
        observed["verifier"] = authorization_verifier
        return ExecutionReceipt(
            operation_id=action.operation_id,
            operation=action.operation,
            target_id=action.target_id,
            plan_id=action.plan_id,
            plan_revision=action.plan_revision,
            authorization_reference_sha256="a" * 64,
            transport_argv=("ssh", "-s", "cybercore-exec"),
            started_at="2026-11-12T00:00:00Z",
            completed_at="2026-11-12T00:00:01Z",
            exit_code=0,
            stdout_sha256="b" * 64,
            stderr_sha256="c" * 64,
            status=ExecutionStatus.EXECUTED,
            mutation_possible=True,
            secret_values_recorded=False,
        )

    monkeypatch.setattr(governed_tools, "execute_action", fake_execute)
    verifier = DummyVerifier()
    handler = governed_tools.build_nextcloud_r1_tool_handler(verifier)
    result = handler(
        {
            "operation_id": "NC-R1-113",
            "plan_id": "#113",
            "plan_revision": "draft-1",
            "authorization_reference": "APPROVE-113-BOUND",
        }
    )

    action = observed["action"]
    assert action.operation == "nextcloud.r1.offhost.transfer"
    assert action.target_id == governed_tools.NEXTCLOUD_R1_TARGET.id
    assert action.arguments == {}
    assert observed["target"] == governed_tools.NEXTCLOUD_R1_TARGET
    assert observed["verifier"] is verifier
    assert result["authorization_reference_sha256"] == "a" * 64
    assert result["secret_values_recorded"] is False
    assert "APPROVE-113-BOUND" not in str(result)


def test_governed_handler_rejects_host_path_or_command_expansion() -> None:
    handler = governed_tools.build_nextcloud_r1_tool_handler(DummyVerifier())
    base = {
        "operation_id": "NC-R1-113",
        "plan_id": "#113",
        "plan_revision": "draft-1",
        "authorization_reference": "APPROVE-113-BOUND",
    }
    for key, value in (
        ("host", "example.invalid"),
        ("path", "/tmp"),
        ("cmd", "id"),
    ):
        payload = dict(base)
        payload[key] = value
        try:
            handler(payload)
        except ValueError as exc:
            assert "exact schema" in str(exc)
        else:
            raise AssertionError(f"unexpected argument accepted: {key}")
