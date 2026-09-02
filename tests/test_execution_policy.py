from cybercore.execution.models import ExecutionTarget, GovernedAction
from cybercore.execution.policy import VIKUNJA_TARGET, evaluate_action


def _action(operation: str = "vikunja.backup.run", **overrides: object) -> GovernedAction:
    values = {
        "operation_id": "A6-OPERATIONS",
        "operation": operation,
        "target_id": "tasks.cyberdjs.org",
        "plan_id": "A6",
        "plan_revision": "1",
        "authorization_reference": "APPROVE-A6-OPERATIONS",
        "arguments": {},
    }
    values.update(overrides)
    return GovernedAction(**values)  # type: ignore[arg-type]


def test_accepts_exact_vikunja_operation() -> None:
    decision = evaluate_action(_action(), VIKUNJA_TARGET)
    assert decision.allowed is True
    assert decision.mutating is True


def test_rejects_unknown_operation() -> None:
    decision = evaluate_action(_action("shell.run"), VIKUNJA_TARGET)
    assert decision.allowed is False


def test_rejects_wrong_host_even_with_same_target_id() -> None:
    target = ExecutionTarget(
        id="tasks.cyberdjs.org",
        hostname="example.invalid",
        ssh_user="cybercore-exec",
    )
    assert evaluate_action(_action(), target).allowed is False


def test_rejects_extra_arguments() -> None:
    assert evaluate_action(_action(arguments={"cmd": "id"}), VIKUNJA_TARGET).allowed is False


def test_rejects_missing_plan_binding() -> None:
    assert evaluate_action(_action(plan_revision=""), VIKUNJA_TARGET).allowed is False
