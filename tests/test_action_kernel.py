from datetime import datetime, timedelta, timezone

from cybercore.action_kernel import (
    ACTION_KERNEL_SCHEMA_VERSION,
    NEXUS_ACTION_CONTRACT,
    NEXUS_CAPABILITY_CONTRACT,
    NEXUS_PROVENANCE_CONTRACT,
    ActionKernel,
    AuditEvent,
    CapabilityDescriptor,
    Provenance,
    TaskRequest,
)


ACTOR = "chatgpt:johnny-work"


def provenance(**changes: object) -> Provenance:
    values = dict(
        source="chatgpt",
        adapter="cybercore-action-kernel-client",
        source_instance="test-client",
        observed_at=datetime.now(timezone.utc),
        confidence="verified",
    )
    values.update(changes)
    return Provenance(**values)  # type: ignore[arg-type]


def task(**changes: object) -> TaskRequest:
    requested_at = datetime.now(timezone.utc)
    values = dict(
        task_id="t1",
        correlation_id="c1",
        actor=ACTOR,
        capability="diagnostics.synthetic_status.v1",
        target_id="herrerbook",
        arguments={},
        requested_at=requested_at,
        expires_at=requested_at + timedelta(minutes=2),
        provenance=provenance(),
    )
    values.update(changes)
    return TaskRequest(**values)  # type: ignore[arg-type]


def kernel(**changes: object) -> ActionKernel:
    opts = dict(
        targets={"herrerbook": {"synthetic_status": "offline"}},
        allowed_actors=frozenset({ACTOR}),
        enabled=True,
        evidence_sink=lambda _: None,
    )
    opts.update(changes)
    return ActionKernel(**opts)  # type: ignore[arg-type]


def test_synthetic_receipt_policy_evidence_and_audit_chain_are_bounded() -> None:
    events: list[AuditEvent] = []
    k = kernel(evidence_sink=events.append)

    result = k.execute(task(), trusted_actor=ACTOR)

    assert result.status == "EXECUTED"
    assert result.reason == "SYNTHETIC_ONLY"
    assert result.actor == ACTOR
    assert result.schema_version == ACTION_KERNEL_SCHEMA_VERSION
    assert result.nexus_contract == NEXUS_ACTION_CONTRACT
    assert result.policy.decision == "ALLOW"
    assert result.policy.reason == "READ_ONLY_ALLOWED"
    assert result.policy.actor == ACTOR
    assert result.policy.provenance.contract == NEXUS_PROVENANCE_CONTRACT
    assert result.evidence is not None
    assert result.evidence.sha256 == result.evidence_sha256
    assert result.evidence.byte_count > 0
    assert result.evidence.byte_count <= 2048
    assert result.evidence.redacted is True
    assert result.provenance.contract == NEXUS_PROVENANCE_CONTRACT
    assert [event.stage for event in events] == [
        "request",
        "policy",
        "execution",
        "evidence",
    ]
    assert all(event.actor == ACTOR for event in events)
    assert events[-1].evidence_sha256 == result.evidence_sha256

    assert k.execute(task(), trusted_actor=ACTOR).reason == "DUPLICATE"


def test_feature_disabled_untrusted_and_spoofed_actor_fail_closed() -> None:
    result_1 = kernel(enabled=False).execute(task(), trusted_actor=ACTOR)
    assert result_1.reason == "FEATURE_DISABLED"
    assert result_1.policy.decision == "DENY"

    result_2 = kernel().execute(task(actor="chatgpt:attacker"), trusted_actor=ACTOR)
    assert result_2.reason == "ACTOR_MISMATCH"
    assert result_2.actor == ACTOR

    result_3 = kernel(allowed_actors=frozenset({ACTOR, "chatgpt:attacker"})).execute(
        task(actor="chatgpt:attacker"),
        trusted_actor="chatgpt:attacker",
    )
    assert result_3.status == "EXECUTED"

    result_4 = kernel().execute(task(actor="chatgpt:attacker"), trusted_actor="chatgpt:attacker")
    assert result_4.reason == "ACTOR_DENIED"


def test_denies_unknown_capability_target_and_arguments() -> None:
    result_1 = kernel().execute(task(capability="terminal.execute"), trusted_actor=ACTOR)
    assert result_1.reason == "CAPABILITY_DENIED"

    result_2 = kernel().execute(task(target_id="external"), trusted_actor=ACTOR)
    assert result_2.reason == "TARGET_DENIED"

    result_3 = kernel().execute(task(arguments={"command": "id"}), trusted_actor=ACTOR)
    assert result_3.reason == "ARGUMENTS_DENIED"


def test_capability_descriptor_is_exact_read_only_allowlist() -> None:
    invalid_mode = CapabilityDescriptor(
        name="diagnostics.synthetic_status.v1",
        version="1",
        mode="write",  # type: ignore[arg-type]
        allowed_targets=frozenset({"herrerbook"}),
    )
    result_1 = kernel(
        capabilities={invalid_mode.name: invalid_mode},
    ).execute(task(), trusted_actor=ACTOR)
    assert result_1.reason == "CAPABILITY_DESCRIPTOR_INVALID"

    wrong_target = CapabilityDescriptor(
        name="diagnostics.synthetic_status.v1",
        version="1",
        mode="read",
        allowed_targets=frozenset({"other-node"}),
    )
    result_2 = kernel(
        capabilities={wrong_target.name: wrong_target},
    ).execute(task(), trusted_actor=ACTOR)
    assert result_2.reason == "TARGET_DENIED"

    wrong_contract = CapabilityDescriptor(
        name="diagnostics.synthetic_status.v1",
        version="1",
        mode="read",
        allowed_targets=frozenset({"herrerbook"}),
        nexus_contract="capability/v999",
    )
    assert wrong_contract.nexus_contract != NEXUS_CAPABILITY_CONTRACT
    result_3 = kernel(
        capabilities={wrong_contract.name: wrong_contract},
    ).execute(task(), trusted_actor=ACTOR)
    assert result_3.reason == "CAPABILITY_DESCRIPTOR_INVALID"


def test_rejects_expired_naive_reversed_and_oversized_requests() -> None:
    result_1 = kernel().execute(
        task(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
        trusted_actor=ACTOR,
    )
    assert result_1.reason == "EXPIRED"

    result_2 = kernel().execute(
        task(requested_at=datetime.now(), expires_at=datetime.now() + timedelta(minutes=1)),
        trusted_actor=ACTOR,
    )
    assert result_2.reason == "INVALID_TIME"

    now = datetime.now(timezone.utc)
    result_3 = kernel().execute(
        task(requested_at=now, expires_at=now),
        trusted_actor=ACTOR,
    )
    assert result_3.reason == "INVALID_TIME"

    result_4 = kernel(max_input_bytes=10).execute(
        task(arguments={"payload": "x" * 100}),
        trusted_actor=ACTOR,
    )
    assert result_4.reason == "OVERSIZED"


def test_contract_schema_and_provenance_validation_fail_closed() -> None:
    result_1 = kernel().execute(
        task(schema_version="action-kernel/v999"),
        trusted_actor=ACTOR,
    )
    assert result_1.reason == "SCHEMA_DENIED"

    result_2 = kernel().execute(
        task(nexus_contract="action/v999"),
        trusted_actor=ACTOR,
    )
    assert result_2.reason == "CONTRACT_DENIED"

    result_3 = kernel().execute(
        task(provenance=provenance(contract="provenance/v999")),
        trusted_actor=ACTOR,
    )
    assert result_3.reason == "PROVENANCE_INVALID"


def test_fails_closed_when_audit_missing_or_fails() -> None:
    result_1 = kernel(evidence_sink=None).execute(task(), trusted_actor=ACTOR)
    assert result_1.reason == "AUDIT_UNAVAILABLE"
    assert result_1.status == "DENIED"

    def broken(_: AuditEvent) -> None:
        raise RuntimeError("backend unavailable")

    result_2 = kernel(evidence_sink=broken).execute(task(), trusted_actor=ACTOR)
    assert result_2.reason == "AUDIT_FAILED"
    assert result_2.status == "FAILED"


def test_denied_request_audits_request_then_policy_without_execution() -> None:
    events: list[AuditEvent] = []
    result = kernel(evidence_sink=events.append).execute(
        task(capability="terminal.execute"),
        trusted_actor=ACTOR,
    )
    assert result.reason == "CAPABILITY_DENIED"
    assert [event.stage for event in events] == ["request", "policy"]
    assert events[-1].outcome == "DENY"


def test_rejects_malformed_nonjson_and_nonfinite_arguments() -> None:
    result_1 = kernel().execute(task(arguments={"bad": object()}), trusted_actor=ACTOR)
    assert result_1.reason == "INVALID_ARGUMENTS"

    result_2 = kernel().execute(task(arguments={"bad": float("nan")}), trusted_actor=ACTOR)
    assert result_2.reason == "INVALID_ARGUMENTS"


def test_evidence_size_is_bounded_before_receipt_is_accepted() -> None:
    result = kernel(max_evidence_bytes=10).execute(task(), trusted_actor=ACTOR)
    assert result.status == "FAILED"
    assert result.reason == "EVIDENCE_OVERSIZED"
    assert result.evidence is None
