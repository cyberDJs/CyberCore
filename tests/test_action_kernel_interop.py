from datetime import datetime, timedelta, timezone

import pytest

from cybercore.action_kernel import ActionKernel, Provenance, TaskRequest
from cybercore.action_kernel_interop import to_hive_health_dry_run, to_nexus_action_result


def request(**overrides: object) -> TaskRequest:
    now = datetime.now(timezone.utc)
    values = {
        "task_id": "ak-test-1",
        "correlation_id": "corr-test-1",
        "actor": "chatgpt:johnny-work",
        "capability": "diagnostics.synthetic_status.v1",
        "target_id": "herrerbook",
        "arguments": {},
        "requested_at": now,
        "expires_at": now + timedelta(minutes=2),
        "provenance": Provenance("cybercore", "test", "local", now),
    }
    values.update(overrides)
    return TaskRequest(**values)  # type: ignore[arg-type]


def test_hive_adapter_is_strictly_dry_run() -> None:
    output = to_hive_health_dry_run(request(), trusted_actor="chatgpt:johnny-work")
    assert output["action"] == "health_check"
    assert output["dry_run"] is True
    assert output["approval_tokens"] == []
    assert output["payload"] == {}
    assert output["requested_by"] == "chatgpt:johnny-work"


def test_hive_adapter_rejects_spoof_and_mutation() -> None:
    with pytest.raises(ValueError, match="actor mismatch"):
        to_hive_health_dry_run(request(), trusted_actor="chatgpt:attacker")
    with pytest.raises(ValueError, match="unsupported capability"):
        to_hive_health_dry_run(
            request(capability="terminal.execute"), trusted_actor="chatgpt:johnny-work"
        )
    with pytest.raises(ValueError, match="arguments prohibited"):
        to_hive_health_dry_run(
            request(arguments={"command": "id"}), trusted_actor="chatgpt:johnny-work"
        )


def test_nexus_result_shape_for_synthetic_receipt() -> None:
    observed = []
    kernel = ActionKernel(
        targets={"herrerbook": {"synthetic_status": "offline"}},
        allowed_actors=frozenset({"chatgpt:johnny-work"}),
        enabled=True,
        evidence_sink=observed.append,
    )
    receipt = kernel.execute(request(), trusted_actor="chatgpt:johnny-work")
    assert receipt.status == "EXECUTED"
    output = to_nexus_action_result(receipt)
    assert output["contract"] == "action/v1"
    assert output["kind"] == "result"
    assert output["status"] == "completed"
    assert output["providerReceipt"]["evidenceSha256"] == receipt.evidence_sha256


def test_nexus_rejection_exposes_no_evidence() -> None:
    kernel = ActionKernel(
        targets={"herrerbook": {"synthetic_status": "offline"}},
        allowed_actors=frozenset({"chatgpt:johnny-work"}),
        enabled=False,
        evidence_sink=lambda _: None,
    )
    output = to_nexus_action_result(kernel.execute(request(), trusted_actor="chatgpt:johnny-work"))
    assert output["status"] == "rejected"
    assert output["providerReceipt"] is None
    assert output["error"]["code"] == "FEATURE_DISABLED"
