from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Lock

import pytest

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
    assert result.nexus_contract_family == NEXUS_ACTION_CONTRACT
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
    nexus_provenance = result.provenance.as_nexus()
    assert nexus_provenance["contract"] == NEXUS_PROVENANCE_CONTRACT
    assert nexus_provenance["sourceInstance"] == "cybercore-local"
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
        nexus_contract_family="capability/v999",
    )
    assert wrong_contract.nexus_contract_family != NEXUS_CAPABILITY_CONTRACT
    result_3 = kernel(
        capabilities={wrong_contract.name: wrong_contract},
    ).execute(task(), trusted_actor=ACTOR)
    assert result_3.reason == "CAPABILITY_DESCRIPTOR_INVALID"


def test_rejects_expired_naive_reversed_and_oversized_requests() -> None:
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    result_1 = kernel().execute(
        task(
            requested_at=expired_at - timedelta(minutes=1),
            expires_at=expired_at,
        ),
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
        task(nexus_contract_family="action/v999"),
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


def test_explicit_empty_capability_allowlist_stays_empty() -> None:
    result = kernel(capabilities={}).execute(task(), trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "CAPABILITY_DENIED"


def test_missing_synthetic_status_returns_structured_denial() -> None:
    result = kernel(
        targets={"herrerbook": {}},
    ).execute(task(), trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "INVALID_INVENTORY"
    assert result.evidence is None


@pytest.mark.parametrize("rollback_seconds", [7, 60])
def test_process_clock_floor_blocks_partial_and_full_utc_rollback(
    rollback_seconds: int,
) -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: current[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    request = task(
        requested_at=base,
        expires_at=base + timedelta(seconds=5),
    )

    # Real/process time advances beyond expiry while wall time is corrected
    # backward. The process floor must dominate the rolled-back wall clock.
    mono[0] = 110.0
    current[0] = base + timedelta(seconds=10 - rollback_seconds)

    result = k.execute(request, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason in {"EXPIRED", "INVALID_TIME"}
    assert result.authorization_deadline_monotonic is None


def test_process_clock_floor_treats_forward_wall_jump_as_upper_bound() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: current[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    request = task(
        requested_at=base,
        expires_at=base + timedelta(seconds=10),
    )

    mono[0] = 101.0
    current[0] = base + timedelta(seconds=20)

    result = k.execute(request, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"


def test_process_clock_floor_rejects_future_request_after_construction_rollback() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base - timedelta(seconds=7)]
    mono = [100.0]
    k = kernel(
        clock=lambda: current[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    request = task(
        requested_at=base,
        expires_at=base + timedelta(seconds=5),
    )

    result = k.execute(request, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "INVALID_TIME"


def test_process_clock_floor_deadline_equality_fails_closed() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: current[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    request = task(
        requested_at=base,
        expires_at=base + timedelta(seconds=5),
    )

    mono[0] = 105.0
    current[0] = base + timedelta(seconds=4)

    result = k.execute(request, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"


def test_executed_receipt_binds_process_local_monotonic_deadline() -> None:
    now = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    request = task(
        requested_at=now,
        expires_at=now + timedelta(seconds=10),
    )
    result = kernel(
        clock=lambda: now,
        monotonic_clock=lambda: 100.0,
        process_id_provider=lambda: 4242,
    ).execute(request, trusted_actor=ACTOR)

    assert result.status == "EXECUTED"
    assert result.authorization_expires_at == request.expires_at
    assert result.authorization_floor_monotonic == 100.0
    assert result.authorization_deadline_monotonic == 110.0
    assert result.authorization_process_id == 4242


def test_denied_receipt_does_not_mint_monotonic_authority() -> None:
    result = kernel(enabled=False).execute(task(), trusted_actor=ACTOR)

    assert result.status == "DENIED"
    assert result.authorization_floor_monotonic is None
    assert result.authorization_deadline_monotonic is None
    assert result.authorization_process_id is None


@pytest.mark.parametrize("blocked_stage", ["request", "policy"])
def test_blocking_audit_cannot_restart_deadline_after_partial_utc_rollback(
    blocked_stage: str,
) -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base]
    monotonic_now = [100.0]
    expires_at = base + timedelta(seconds=5)
    events: list[AuditEvent] = []

    def sink(event: AuditEvent) -> None:
        events.append(event)
        if event.stage == blocked_stage and (
            blocked_stage == "request" or event.outcome == "ALLOW"
        ):
            # Ten seconds of real elapsed time are hidden behind only three
            # seconds of apparent UTC progress by a seven-second rollback.
            monotonic_now[0] = 110.0
            current[0] = base + timedelta(seconds=3)

    k = kernel(
        evidence_sink=sink,
        clock=lambda: current[0],
        monotonic_clock=lambda: monotonic_now[0],
        process_id_provider=lambda: 4242,
    )
    result = k.execute(
        task(
            requested_at=base,
            expires_at=expires_at,
        ),
        trusted_actor=ACTOR,
    )

    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"
    assert result.authorization_deadline_monotonic is None
    assert result.authorization_process_id is None
    assert any(event.stage == blocked_stage for event in events)


def test_expiry_is_rechecked_after_policy_audit_before_dispatch() -> None:
    current = [datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)]
    expires_at = current[0] + timedelta(seconds=10)
    events: list[AuditEvent] = []

    def sink(event: AuditEvent) -> None:
        events.append(event)
        if event.stage == "policy" and event.outcome == "ALLOW":
            current[0] = expires_at + timedelta(seconds=1)

    k = kernel(evidence_sink=sink, clock=lambda: current[0])
    result = k.execute(
        task(
            requested_at=current[0],
            expires_at=expires_at,
        ),
        trusted_actor=ACTOR,
    )

    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"
    assert result.policy.decision == "DENY"
    assert [event.stage for event in events] == ["request", "policy", "execution"]
    assert events[-1].outcome == "DENIED"
    assert events[-1].reason == "EXPIRED"


def test_task_id_reservation_is_atomic_under_concurrent_dispatch() -> None:
    policy_barrier = Barrier(2)
    event_lock = Lock()
    events: list[AuditEvent] = []

    def sink(event: AuditEvent) -> None:
        if event.stage == "policy" and event.outcome == "ALLOW":
            policy_barrier.wait(timeout=5)
        with event_lock:
            events.append(event)

    k = kernel(evidence_sink=sink)
    request = task()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: k.execute(request, trusted_actor=ACTOR),
                range(2),
            )
        )

    assert sorted((result.status, result.reason) for result in results) == [
        ("DENIED", "DUPLICATE"),
        ("EXECUTED", "SYNTHETIC_ONLY"),
    ]


def test_reserved_task_id_stays_consumed_after_uncertain_dispatch_failure() -> None:
    def sink(event: AuditEvent) -> None:
        if event.stage == "execution":
            raise RuntimeError("audit backend failed after dispatch boundary")

    k = kernel(evidence_sink=sink)
    request = task()

    first = k.execute(request, trusted_actor=ACTOR)
    second = k.execute(request, trusted_actor=ACTOR)

    assert first.status == "FAILED"
    assert first.reason == "AUDIT_FAILED"
    assert second.status == "DENIED"
    assert second.reason == "DUPLICATE"


def test_issue_deadline_caps_forward_utc_jump() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    wall = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )

    # Kernel construction predates a +1h UTC correction. The new request
    # is valid at the observed corrected clock, but not for an hour.
    wall[0] = base + timedelta(hours=1)
    mono[0] = 101.0
    req = task(
        requested_at=wall[0],
        expires_at=wall[0] + timedelta(seconds=5),
    )
    receipt = k.execute(req, trusted_actor=ACTOR)
    assert receipt.status == "EXECUTED"
    assert receipt.authorization_floor_monotonic == 101.0
    assert receipt.authorization_deadline_monotonic == 106.0


def test_kernel_rejects_monotonic_rollback_after_policy_before_authority() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    mono = [100.0]
    wall = [base]

    def audit(event: AuditEvent) -> None:
        if event.stage == "policy" and event.outcome == "ALLOW":
            # Policy already observed monotonic 104; even after a clock
            # rollback with plausible UTC, no new receipt can be issued.
            mono[0] = 101.0
            wall[0] = base + timedelta(seconds=1)

    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
        evidence_sink=audit,
    )
    mono[0] = 104.0
    wall[0] = base + timedelta(seconds=4)
    req = task(requested_at=base, expires_at=base + timedelta(seconds=5))
    with pytest.raises(PermissionError, match="clock authority unavailable"):
        k.execute(req, trusted_actor=ACTOR)


def test_kernel_monotonic_high_water_is_shared_across_requests() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    mono = [100.0]
    wall = [base]
    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    mono[0] = 103.0
    wall[0] = base + timedelta(seconds=3)
    assert (
        k.execute(
            task(task_id="first", requested_at=base, expires_at=base + timedelta(seconds=9)),
            trusted_actor=ACTOR,
        ).status
        == "EXECUTED"
    )

    # A later request cannot mint authority from the regressed counter.
    mono[0] = 102.0
    wall[0] = base + timedelta(seconds=2)
    with pytest.raises(PermissionError, match="clock authority unavailable"):
        k.execute(
            task(task_id="second", requested_at=base, expires_at=base + timedelta(seconds=9)),
            trusted_actor=ACTOR,
        )


def test_forward_utc_during_policy_survives_audit_rollback() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    wall = [base]
    mono = [100.0]
    future = base + timedelta(hours=1)

    def audit(event: AuditEvent) -> None:
        if event.stage == "policy" and event.outcome == "ALLOW":
            # A transient forward jump was observed by policy, then the
            # audit blocks until UTC is corrected backward before issuance.
            wall[0] = base + timedelta(seconds=1)

    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
        evidence_sink=audit,
    )
    wall[0] = future
    mono[0] = 101.0
    request = task(
        task_id="forward-policy-rollback",
        requested_at=future,
        expires_at=future + timedelta(seconds=5),
    )
    receipt = k.execute(request, trusted_actor=ACTOR)
    assert receipt.status == "EXECUTED"
    assert receipt.authorization_floor_monotonic == 101.0
    assert receipt.authorization_deadline_monotonic == 106.0
    assert receipt.authorization_deadline_monotonic < 110.0


def test_kernel_utc_high_water_is_shared_across_separate_requests() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    wall = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    forward = base + timedelta(hours=1)
    wall[0] = forward
    mono[0] = 101.0
    first = task(
        task_id="forward-utc-first",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=5),
    )
    assert k.execute(first, trusted_actor=ACTOR).status == "EXECUTED"

    wall[0] = base + timedelta(seconds=1)
    mono[0] = 102.0
    second = task(
        task_id="after-utc-rollback",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=5),
    )
    receipt = k.execute(second, trusted_actor=ACTOR)
    assert receipt.status == "EXECUTED"
    # The forward UTC observation occurred at monotonic 101, so its
    # five-second deadline remains 106 even when checked later at 102.
    assert receipt.authorization_deadline_monotonic == 106.0


def test_forward_utc_peak_expires_during_blocking_policy_audit() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    forward = base + timedelta(hours=1)
    wall = [base]
    mono = [100.0]

    def audit(event: AuditEvent) -> None:
        if event.stage == "policy" and event.outcome == "ALLOW":
            # Peak sampled at monotonic 101; ten seconds later the wall
            # clock has rolled back but the five-second grant is expired.
            mono[0] = 111.0
            wall[0] = base + timedelta(seconds=1)

    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
        evidence_sink=audit,
    )
    wall[0] = forward
    mono[0] = 101.0
    req = task(
        task_id="forward-peak-audit-delay",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=5),
    )
    result = k.execute(req, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"
    assert result.authorization_deadline_monotonic is None


def test_forward_utc_peak_deadline_equality_denies_after_rollback() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    forward = base + timedelta(hours=1)
    wall = [base]
    mono = [100.0]

    def audit(event: AuditEvent) -> None:
        if event.stage == "policy" and event.outcome == "ALLOW":
            mono[0] = 106.0
            wall[0] = base + timedelta(seconds=1)

    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
        evidence_sink=audit,
    )
    wall[0] = forward
    mono[0] = 101.0
    req = task(
        task_id="forward-peak-equality",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=5),
    )
    result = k.execute(req, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"


def test_later_wall_value_cannot_lower_projected_utc_peak() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    forward = base + timedelta(hours=1)
    wall = [base]
    mono = [100.0]
    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )

    wall[0] = forward
    mono[0] = 101.0
    first = task(
        task_id="forward-utc-peak-anchor",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=15),
    )
    assert k.execute(first, trusted_actor=ACTOR).status == "EXECUTED"

    # At monotonic 120, the peak projects to forward+19 seconds.
    # UTC forward+1 is larger than the raw stored peak but must not reset
    # its monotonic anchor or revive a grant already expired at 116.
    mono[0] = 120.0
    wall[0] = forward + timedelta(seconds=1)
    second = task(
        task_id="late-wall-below-projected-peak",
        requested_at=forward,
        expires_at=forward + timedelta(seconds=15),
    )
    result = k.execute(second, trusted_actor=ACTOR)
    assert result.status == "DENIED"
    assert result.reason == "EXPIRED"
    assert result.authorization_deadline_monotonic is None


@pytest.mark.parametrize("blocked_stage", ["execution", "evidence"])
def test_post_authorization_audit_revalidates_floor_after_partial_utc_rollback(
    blocked_stage: str,
) -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    current = [base]
    monotonic_now = [100.0]
    expires_at = base + timedelta(seconds=5)
    events: list[AuditEvent] = []

    def sink(event: AuditEvent) -> None:
        events.append(event)
        if event.stage == blocked_stage:
            # Ten seconds of process time elapse while UTC shows only three:
            # the final authority sample must project from the construction
            # floor and refuse to mint a stale bridge-capable receipt.
            monotonic_now[0] = 110.0
            current[0] = base + timedelta(seconds=3)

    k = kernel(
        evidence_sink=sink,
        clock=lambda: current[0],
        monotonic_clock=lambda: monotonic_now[0],
        process_id_provider=lambda: 4242,
    )
    request = task(
        task_id=f"post-audit-{blocked_stage}",
        correlation_id=f"corr-post-audit-{blocked_stage}",
        requested_at=base,
        expires_at=expires_at,
    )

    result = k.execute(request, trusted_actor=ACTOR)

    assert result.status == "FAILED"
    assert result.reason == "EXPIRED"
    assert result.authorization_floor_monotonic is None
    assert result.authorization_deadline_monotonic is None
    assert result.authorization_process_id is None
    assert any(event.stage == blocked_stage for event in events)

    # Reservation stays consumed after crossing the execution boundary.
    # Use a fresh, time-valid request so expiry ordering cannot mask DUPLICATE.
    current[0] = base + timedelta(seconds=10)
    duplicate_request = task(
        task_id=request.task_id,
        correlation_id=request.correlation_id,
        requested_at=current[0],
        expires_at=current[0] + timedelta(seconds=5),
    )
    duplicate = k.execute(duplicate_request, trusted_actor=ACTOR)
    assert duplicate.status == "DENIED"
    assert duplicate.reason == "DUPLICATE"


def test_invalid_monotonic_observation_latches_kernel_fail_closed() -> None:
    base = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    mono = [100.0]
    wall = [base]
    k = kernel(
        clock=lambda: wall[0],
        monotonic_clock=lambda: mono[0],
        process_id_provider=lambda: 4242,
    )
    mono[0] = 110.0
    wall[0] = base + timedelta(seconds=10)
    assert (
        k.execute(
            task(
                task_id="clock-first",
                requested_at=base,
                expires_at=base + timedelta(seconds=30),
            ),
            trusted_actor=ACTOR,
        ).status
        == "EXECUTED"
    )
    mono[0] = 109.0
    with pytest.raises(PermissionError, match="clock authority unavailable"):
        k.execute(
            task(
                task_id="clock-rollback",
                requested_at=base,
                expires_at=base + timedelta(seconds=30),
            ),
            trusted_actor=ACTOR,
        )

    # A later plausible observation must not silently reset the sticky fence.
    mono[0] = 111.0
    wall[0] = base + timedelta(seconds=11)
    with pytest.raises(PermissionError, match="clock authority unavailable"):
        k.execute(
            task(
                task_id="clock-after-rollback",
                requested_at=base,
                expires_at=base + timedelta(seconds=30),
            ),
            trusted_actor=ACTOR,
        )
