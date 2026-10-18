from datetime import datetime, timedelta, timezone

from cybercore.action_kernel import ActionKernel, TaskRequest


def task(**changes: object) -> TaskRequest:
    values = dict(
        task_id="t1",
        correlation_id="c1",
        capability="diagnostics.synthetic_status.v1",
        target_id="herrerbook",
        arguments={},
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    values.update(changes)
    return TaskRequest(**values)  # type: ignore[arg-type]


def kernel(**changes: object) -> ActionKernel:
    opts = dict(
        targets={"herrerbook": {"synthetic_status": "offline"}},
        allowed_actors=frozenset({"chatgpt:johnny-work"}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    opts.update(changes)
    return ActionKernel(**opts)  # type: ignore[arg-type]


def test_synthetic_receipt_and_duplicate_are_bounded() -> None:
    k = kernel()
    result = k.execute(task(), trusted_actor="chatgpt:johnny-work")
    assert result.status == "EXECUTED"
    assert result.reason == "SYNTHETIC_ONLY"
    assert result.evidence_sha256 is not None
    assert k.execute(task(), trusted_actor="chatgpt:johnny-work").reason == "DUPLICATE"


def test_feature_disabled_and_untrusted_actor() -> None:
    result_1 = kernel(enabled=False).execute(task(), trusted_actor="chatgpt:johnny-work")
    assert result_1.reason == "FEATURE_DISABLED"
    assert kernel().execute(task(), trusted_actor="chatgpt:attacker").reason == "ACTOR_DENIED"


def test_denies_unknown_capability_target_and_arguments() -> None:
    result_2 = kernel().execute(task(capability="terminal.execute"), trusted_actor="chatgpt:johnny-work")
    assert result_2.reason == "CAPABILITY_DENIED"
    result_3 = kernel().execute(task(target_id="external"), trusted_actor="chatgpt:johnny-work")
    assert result_3.reason == "TARGET_DENIED"
    result_4 = kernel().execute(task(arguments={"command": "id"}), trusted_actor="chatgpt:johnny-work")
    assert result_4.reason == "ARGUMENTS_DENIED"


def test_rejects_expired_naive_and_oversized() -> None:
    actor = "chatgpt:johnny-work"
    result_5 = kernel().execute(task(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), trusted_actor=actor)
    assert result_5.reason == "EXPIRED"
    result_6 = kernel().execute(task(expires_at=datetime.now()), trusted_actor=actor)
    assert result_6.reason == "EXPIRED"
    result_7 = kernel(max_input_bytes=10).execute(task(arguments={"payload": "x" * 100}), trusted_actor=actor)
    assert result_7.reason == "OVERSIZED"


def test_fails_closed_when_audit_missing_or_fails() -> None:
    actor = "chatgpt:johnny-work"
    result_8 = kernel(evidence_sink=None).execute(task(), trusted_actor=actor)
    assert result_8.reason == "AUDIT_UNAVAILABLE"

    def broken(_: object) -> None:
        raise RuntimeError("backend unavailable")

    k = kernel(evidence_sink=broken)
    assert k.execute(task(), trusted_actor=actor).reason == "AUDIT_FAILED"


def test_rejects_malformed_or_nonjson_arguments() -> None:
    actor = "chatgpt:johnny-work"
    result_9 = kernel().execute(task(arguments={"bad": object()}), trusted_actor=actor)
    assert result_9.reason == "INVALID_ARGUMENTS"
