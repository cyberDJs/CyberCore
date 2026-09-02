from cybercore.execution.models import ExecutionStatus, GovernedAction
from cybercore.execution.receipt import build_receipt, digest_bytes


def test_receipt_contains_digests_not_output() -> None:
    action = GovernedAction(
        operation_id="A6-OPERATIONS",
        operation="vikunja.health.verify",
        target_id="tasks.cyberdjs.org",
        plan_id="A6",
        plan_revision="1",
        authorization_reference="APPROVE-A6-OPERATIONS",
    )
    receipt = build_receipt(
        action,
        transport_argv=("ssh", "example"),
        started_at="2026-09-02T00:00:00Z",
        completed_at="2026-09-02T00:00:01Z",
        exit_code=0,
        stdout=b"potentially sensitive output",
        stderr=b"",
        mutation_possible=False,
    )
    assert receipt.status is ExecutionStatus.EXECUTED
    assert receipt.stdout_sha256 == digest_bytes(b"potentially sensitive output")
    assert receipt.secret_values_recorded is False
    assert not hasattr(receipt, "stdout")


def test_nonzero_exit_is_failed() -> None:
    action = GovernedAction(
        operation_id="A6-OPERATIONS",
        operation="vikunja.backup.run",
        target_id="tasks.cyberdjs.org",
        plan_id="A6",
        plan_revision="1",
        authorization_reference="APPROVE-A6-OPERATIONS",
    )
    receipt = build_receipt(
        action,
        transport_argv=("ssh", "example"),
        started_at="2026-09-02T00:00:00Z",
        completed_at="2026-09-02T00:00:01Z",
        exit_code=23,
        stdout=b"",
        stderr=b"failure",
        mutation_possible=True,
    )
    assert receipt.status is ExecutionStatus.FAILED
