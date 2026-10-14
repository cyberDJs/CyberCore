"""Named F01-F10 / T01-T10 tests for ADR-0014 (simulation only)."""

from __future__ import annotations

import json

import pytest

from cybercore.failover_sim import (
    AuditUnavailable,
    Clock,
    FakeProvider,
    Journal,
    Request,
    SimulatedCrash,
    Simulator,
    UnsafeEffect,
)


@pytest.fixture
def env(tmp_path):
    journal = Journal(tmp_path / "ledger.sqlite3")
    provider = FakeProvider()
    sim = Simulator(journal, provider, Clock())
    sim.grant("Ruku", "service_a", "restart")
    sim.lease("Ruku")
    sim.allow()
    yield sim
    journal.close()


def request(operation_id="op-1", **kwargs):
    return Request(operation_id=operation_id, **kwargs)


def broken_restart(sim, operation_id="unhealthy"):
    sim.provider.fail_restart = True
    req = request(operation_id)
    assert sim.run(req) == "UNKNOWN"
    return req


def test_F01_kato_crash_before_effect(env):
    r = request()
    with pytest.raises(SimulatedCrash):
        env.run(r, crash="before_effect")
    assert env.journal.get(r.operation_id)["state"] == "PREPARED"
    assert env.reconcile(r) == "UNKNOWN"
    assert not env.provider.effects


def test_F02_kato_crash_after_effect(env):
    r = request()
    with pytest.raises(SimulatedCrash):
        env.run(r, crash="after_effect")
    assert len(env.provider.effects) == 1
    assert env.reconcile(r) == "SUCCEEDED"
    assert len(env.provider.effects) == 1


def test_F03_ruku_outage_bounded_failover(env):
    env.grant("CyberCore", "service_a", "restart")
    env.lease("CyberCore", takeover=True)
    assert env.run(request(actor="CyberCore")) == "SUCCEEDED"
    assert env.run(request("old-ruku")) == "STOPPED"
    assert len(env.provider.effects) == 1


def test_F04_ruku_return_handback_fences_old_controller(env):
    env.grant("CyberCore", "service_a", "restart")
    env.lease("CyberCore", takeover=True)
    assert env.run(request(actor="CyberCore")) == "SUCCEEDED"
    env.lease("Ruku", takeover=True)
    assert env.run(request("old-core", actor="CyberCore")) == "STOPPED"
    assert env.run(request("new-ruku")) == "SUCCEEDED"
    assert len(env.provider.effects) == 2


def test_F05_voodoo_deny_and_timeout_veto_recovery(env):
    r = broken_restart(env)
    env.allow(decision="DENY")
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore", decision="DENY")
    assert env.compensate(r) == "RECOVERY_BLOCKED"
    assert len(env.provider.effects) == 1
    assert env.alerts


def test_F06_failed_restart_verified_recovery(env):
    r = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    assert env.compensate(r) == "SUCCEEDED"
    assert env.provider.health["service_a"]


def test_F07_stale_inventory_and_unknown_target(env):
    assert env.run(request(inventory_fresh=False)) == "STOPPED"
    assert env.run(request("bad-target", target="ssh://10.0.1.138")) == "STOPPED"
    assert not env.provider.effects


def test_F08_partition_two_leaders_old_epoch_rejected(env):
    old = env.journal.current_lease("service_a")
    env.grant("CyberCore", "service_a", "restart")
    env.lease("CyberCore", takeover=True)
    with pytest.raises(UnsafeEffect):
        env.provider.mutate("service_a", "restart", old.epoch, "old-command")
    assert env.run(request(actor="CyberCore")) == "SUCCEEDED"


def test_F09_red_requires_scoped_human_authorization(env):
    r = request(tier="RED", human_approval="agent")
    assert env.run(r) == "STOPPED"
    assert len(env.provider.effects) == 0
    env.human_approvals.add("red-approved")
    assert env.run(request("red-approved", tier="RED", human_approval="Jan Kočí")) == "SUCCEEDED"


def test_F10_orphaned_operation_reconciled_after_restart(tmp_path):
    file = tmp_path / "ledger.sqlite3"
    provider = FakeProvider()
    first = Simulator(Journal(file), provider)
    first.grant("Ruku", "service_a", "restart")
    first.lease("Ruku")
    first.allow()
    req = request()
    with pytest.raises(SimulatedCrash):
        first.run(req, crash="after_effect")
    first.journal.close()
    second = Simulator(Journal(file), provider)
    assert second.reconcile(req) == "SUCCEEDED"
    assert len(provider.effects) == 1
    second.journal.close()


def test_T01_deduplicated_dispatch_and_unknown_without_idempotency(tmp_path):
    e = env_from(tmp_path, idempotency=True)
    req = request()
    with pytest.raises(SimulatedCrash):
        e.run(req, crash="before_effect")
    assert e.reconcile(req, retry=True) == "SUCCEEDED"
    assert len(e.provider.effects) == 1
    assert e.reconcile(req, retry=True) == "SUCCEEDED"
    e.journal.close()
    e = env_from(tmp_path / "other", idempotency=False)
    req = request()
    with pytest.raises(SimulatedCrash):
        e.run(req, crash="during_effect")
    assert e.reconcile(req, retry=True) == "UNKNOWN"
    assert not e.provider.effects
    e.journal.close()


def env_from(tmp_path, *, idempotency=True):
    tmp_path.mkdir(exist_ok=True, parents=True)
    journal = Journal(tmp_path / "journal.sqlite3")
    p = FakeProvider(idempotency=idempotency)
    s = Simulator(journal, p)
    s.grant("Ruku", "service_a", "restart")
    s.lease("Ruku")
    s.allow()
    return s


def test_T02_capability_and_lease_independent_gates(tmp_path):
    e = Simulator(Journal(tmp_path / "no-lease.sqlite3"), FakeProvider())
    e.grant("Ruku", "service_a", "restart")
    e.allow()
    assert e.run(request()) == "STOPPED"
    e.lease("Ruku")
    assert e.run(request("valid")) == "SUCCEEDED"
    e.capabilities.clear()
    assert e.run(request("no-cap")) == "STOPPED"
    e.journal.close()


def test_T03_partition_unfenced_adapter_refuses_lease(tmp_path):
    p = FakeProvider(fencing=False)
    s = Simulator(Journal(tmp_path / "j.sqlite3"), p)
    with pytest.raises(UnsafeEffect):
        s.lease("CyberCore")
    assert not p.effects
    s.journal.close()


def test_T04_return_handback_preserves_exclusivity(env):
    env.grant("CyberCore", "service_a", "restart")
    lease1 = env.journal.current_lease("service_a")
    lease2 = env.lease("CyberCore", takeover=True)
    assert lease2.epoch > lease1.epoch
    lease3 = env.lease("Ruku", takeover=True)
    assert lease3.epoch > lease2.epoch
    with pytest.raises(UnsafeEffect):
        env.provider.mutate("service_a", "restart", lease2.epoch, "stale")


@pytest.mark.parametrize(
    "decision,valid,ttl",
    [("DENY", True, 60), ("UNKNOWN", True, 60), ("ALLOW", False, 60), ("ALLOW", True, 0)],
)
def test_T05_security_veto_including_corrupt_and_timeout(env, decision, valid, ttl):
    env.allow(decision=decision, valid=valid, ttl=ttl)
    assert env.run(request()) == "STOPPED"
    assert not env.provider.effects


def test_T06_stale_inventory_or_missing_restore_blocks(env):
    assert env.run(request(inventory_fresh=False)) == "STOPPED"
    assert env.run(request("no-restore", restore_verified=False)) == "STOPPED"
    assert not env.provider.effects


def test_T07_compensation_failed_and_blocked(tmp_path):
    e = env_from(tmp_path / "failed")
    r = broken_restart(e)
    e.grant("Ruku", "service_a", "restore")
    e.allow(action="restore")
    e.provider.fail_restore = True
    assert e.compensate(r) == "RECOVERY_FAILED"
    assert e.journal.get(r.operation_id)["state"] == "RECOVERY_FAILED"
    e.journal.close()
    e = env_from(tmp_path / "blocked")
    r = broken_restart(e)
    e.grant("Ruku", "service_a", "restore")
    e.allow(action="restore", decision="DENY")
    assert e.compensate(r) == "RECOVERY_BLOCKED"
    assert len(e.provider.effects) == 1
    e.journal.close()


def test_T08_durable_event_sequence_after_crash_and_restart(tmp_path):
    file = tmp_path / "journal.sqlite3"
    provider = FakeProvider()
    e = Simulator(Journal(file), provider)
    e.grant("Ruku", "service_a", "restart")
    e.lease("Ruku")
    e.allow()
    with pytest.raises(SimulatedCrash):
        e.run(request(), crash="after_effect")
    e.journal.close()
    e = Simulator(Journal(file), provider)
    assert e.reconcile(request()) == "SUCCEEDED"
    events = e.journal.events("op-1")
    assert [x["seq"] for x in events] == list(range(1, len(events) + 1))
    assert [x["state"] for x in events][-1] == "SUCCEEDED"
    e.journal.close()


def test_T09_expired_capability_expired_lease_wrong_policy_target(env):
    env.clock.advance(61)
    assert env.run(request()) == "STOPPED"
    env.grant("Ruku", "service_a", "restart")
    assert env.run(request("lease-expired")) == "STOPPED"
    env.lease("Ruku")
    env.allow()
    assert env.run(request("wrong-policy", policy_hash="other-policy")) == "STOPPED"
    assert env.run(request("wrong-target", target="service_b")) == "STOPPED"
    assert not env.provider.effects


def test_T10_audit_write_failure_fails_closed(env):
    env.journal.fail_writes = True
    with pytest.raises(AuditUnavailable):
        env.run(request())
    assert len(env.provider.effects) == 0
    env.journal.fail_writes = False
    assert env.run(request("later")) == "SUCCEEDED"


def test_production_targets_unrepresentable(env):
    for target in (
        "https://prod.example",
        "ssh://host",
        "10.0.1.138",
        "prod.example",
        "../../hosts",
    ):
        assert (
            env.run(request(f"bad-{len(env.provider.effects)}-{target}", target=target))
            == "STOPPED"
        )
    assert env.run(request("production", production=True)) == "STOPPED"
    assert len(env.provider.effects) == 0


def test_duplicate_operation_rejected(env):
    assert env.run(request()) == "SUCCEEDED"
    with pytest.raises(UnsafeEffect):
        env.run(request())
    assert len(env.provider.effects) == 1


def test_deterministic_normalized_audit_traces(tmp_path):
    def trace(path):
        s = env_from(path)
        assert s.run(request()) == "SUCCEEDED"
        out = s.journal.events("op-1")
        s.journal.close()
        return [{k: v for k, v in record.items() if k != "seq"} for record in out]

    assert trace(tmp_path / "a") == trace(tmp_path / "b")
    serialized = json.dumps(trace(tmp_path / "c"))
    assert "capability_id" in serialized and "lease_id" in serialized
    assert "policy_hash" in serialized and "voodoo" in serialized
    assert "password" not in serialized.lower() and "token" not in serialized.lower()


def test_exclusive_controller_lease_without_takeover_is_refused(env):
    with pytest.raises(UnsafeEffect):
        env.lease("CyberCore")


def test_provider_unreadable_results_unknown_and_no_retry(env):
    req = request()
    with pytest.raises(SimulatedCrash):
        env.run(req, crash="after_effect")
    env.provider.readable = False
    assert env.reconcile(req, retry=True) == "UNKNOWN"
    assert len(env.provider.effects) == 1


def test_unreconciled_operation_blocks_new_write_until_readonly_recovery(env):
    first = request("first")
    with pytest.raises(SimulatedCrash):
        env.run(first, crash="after_effect")
    assert env.run(request("second")) == "STOPPED"
    assert len(env.provider.effects) == 1
    assert env.reconcile(first) == "SUCCEEDED"
    assert env.run(request("third")) == "SUCCEEDED"


def test_reconciliation_cannot_replace_actor_or_policy_from_journal(env):
    req = request()
    with pytest.raises(SimulatedCrash):
        env.run(req, crash="after_effect")
    for replacement in (
        request(actor="CyberCore"),
        request(policy_hash="new-policy"),
        request(correlation_id="forged"),
    ):
        with pytest.raises(UnsafeEffect):
            env.reconcile(replacement)
    assert env.reconcile(req) == "SUCCEEDED"


def test_compensation_cannot_replace_actor_from_journal(env):
    req = broken_restart(env)
    env.grant("CyberCore", "service_a", "restore")
    env.lease("CyberCore", takeover=True)
    env.allow(action="restore")
    with pytest.raises(UnsafeEffect):
        env.compensate(request(req.operation_id, actor="CyberCore"))


def test_recheck_voodoo_before_effect_boundary(env, monkeypatch):
    original = env._transition

    def revoke_after_executing(req, state, **kwargs):
        original(req, state, **kwargs)
        if state == "EXECUTING":
            env.allow(decision="DENY")

    monkeypatch.setattr(env, "_transition", revoke_after_executing)
    assert env.run(request()) == "STOPPED"
    assert len(env.provider.effects) == 0


@pytest.mark.parametrize("revoked_gate", ("voodoo", "capability", "lease"))
def test_reconcile_rechecks_authority_after_executing_checkpoint(env, monkeypatch, revoked_gate):
    req = request("retry-gate-revoked")
    with pytest.raises(SimulatedCrash):
        env.run(req, crash="before_effect")
    transition = env._transition

    def revoke_after_checkpoint(req, state, **kwargs):
        transition(req, state, **kwargs)
        if state == "EXECUTING":
            if revoked_gate == "voodoo":
                env.allow(decision="DENY")
            elif revoked_gate == "capability":
                env.capabilities.clear()
            else:
                env.lease("CyberCore", takeover=True)

    monkeypatch.setattr(env, "_transition", revoke_after_checkpoint)
    assert env.reconcile(req, retry=True) == "STOPPED"
    assert env.journal.get(req.operation_id)["state"] == "STOPPED"
    assert not env.provider.effects


@pytest.mark.parametrize("revoked_gate", ("voodoo", "capability", "lease"))
def test_compensation_rechecks_restore_gate_after_recovering_checkpoint(
    env, monkeypatch, revoked_gate
):
    req = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    transition = env._transition

    def revoke_after_checkpoint(req, state, **kwargs):
        transition(req, state, **kwargs)
        if state == "RECOVERING":
            if revoked_gate == "voodoo":
                env.allow(action="restore", decision="DENY")
            elif revoked_gate == "capability":
                env.capabilities.pop(("Ruku", "service_a", "restore"))
            else:
                env.lease("CyberCore", takeover=True)

    monkeypatch.setattr(env, "_transition", revoke_after_checkpoint)
    assert env.compensate(req) == "RECOVERY_BLOCKED"
    assert env.journal.get(req.operation_id)["state"] == "RECOVERY_BLOCKED"
    assert len(env.provider.effects) == 1


def test_compensation_events_record_restore_authority_not_restart(env):
    req = broken_restart(env)
    env.allow(decision="DENY")
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    assert env.compensate(req) == "SUCCEEDED"
    for event in env.journal.events(req.operation_id)[-3:]:
        assert event["state"] in {"RECOVERING", "VERIFYING", "SUCCEEDED"}
        assert event["capability_id"] == "grant-Ruku-service_a-restore"
        assert event["voodoo"] == "ALLOW"


def test_normal_post_effect_observation_outage_persists_unknown(env):
    env.provider.readable = False
    req = request()
    assert env.run(req) == "UNKNOWN"
    assert env.journal.get(req.operation_id)["state"] == "UNKNOWN"
    assert len(env.provider.effects) == 1
    assert env.alerts and "UNKNOWN" in env.alerts[-1]


def test_retry_post_effect_observation_outage_persists_unknown(env, monkeypatch):
    req = request("retry-observation")
    with pytest.raises(SimulatedCrash):
        env.run(req, crash="before_effect")
    mutate = env.provider.mutate

    def lose_observation_after_effect(*args):
        receipt = mutate(*args)
        env.provider.readable = False
        return receipt

    monkeypatch.setattr(env.provider, "mutate", lose_observation_after_effect)
    assert env.reconcile(req, retry=True) == "UNKNOWN"
    assert env.journal.get(req.operation_id)["state"] == "UNKNOWN"
    assert len(env.provider.effects) == 1


def test_restore_post_effect_observation_outage_persists_unknown(env, monkeypatch):
    req = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    mutate = env.provider.mutate

    def lose_observation_after_restore(*args):
        receipt = mutate(*args)
        env.provider.readable = False
        return receipt

    monkeypatch.setattr(env.provider, "mutate", lose_observation_after_restore)
    assert env.compensate(req) == "RECOVERY_UNKNOWN"
    assert env.journal.get(req.operation_id)["state"] == "RECOVERY_UNKNOWN"
    assert len(env.provider.effects) == 2
    assert env.alerts and "RECOVERY_UNKNOWN" in env.alerts[-1]


@pytest.mark.parametrize("revocation", ("voodoo", "capability", "lease"))
def test_retry_effect_dispatch_rechecks_after_last_preflight(env, monkeypatch, revocation):
    req = request("retry-last-window")
    with pytest.raises(SimulatedCrash):
        env.run(req, crash="before_effect")
    original = env.provider.mutate

    def revoke_at_dispatch(*args):
        if revocation == "voodoo":
            env.allow(decision="DENY")
        elif revocation == "capability":
            env.capabilities.clear()
        else:
            env.lease("CyberCore", takeover=True)
        return original(*args)

    monkeypatch.setattr(env.provider, "mutate", revoke_at_dispatch)
    assert env.reconcile(req, retry=True) == "STOPPED"
    assert not env.provider.effects


@pytest.mark.parametrize("revocation", ("voodoo", "capability", "lease"))
def test_restore_effect_dispatch_rechecks_after_last_preflight(env, monkeypatch, revocation):
    req = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    original = env.provider.mutate

    def revoke_at_dispatch(*args):
        if revocation == "voodoo":
            env.allow(action="restore", decision="DENY")
        elif revocation == "capability":
            env.capabilities.pop(("Ruku", "service_a", "restore"))
        else:
            env.lease("CyberCore", takeover=True)
        return original(*args)

    monkeypatch.setattr(env.provider, "mutate", revoke_at_dispatch)
    assert env.compensate(req) in {"RECOVERY_BLOCKED", "RECOVERY_FAILED"}
    assert len(env.provider.effects) == 1


def test_restore_audit_uses_effect_snapshot_after_revocation(env, monkeypatch):
    req = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    original = env.provider.mutate

    def revoke_after_effect(*args):
        result = original(*args)
        env.allow(action="restore", decision="DENY")
        env.capabilities.pop(("Ruku", "service_a", "restore"))
        return result

    monkeypatch.setattr(env.provider, "mutate", revoke_after_effect)
    assert env.compensate(req) == "SUCCEEDED"
    for event in env.journal.events(req.operation_id)[-2:]:
        assert event["state"] in {"VERIFYING", "SUCCEEDED"}
        assert event["capability_id"] == "grant-Ruku-service_a-restore"
        assert event["voodoo"] == "ALLOW"


def test_recovery_unknown_reconciles_restore_receipt_not_restart(env, monkeypatch):
    req = broken_restart(env)
    restart_receipt = env.provider.receipts[req.operation_id][3]
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    original = env.provider.mutate

    def unreadable_after_restore(*args):
        receipt = original(*args)
        env.provider.readable = False
        return receipt

    monkeypatch.setattr(env.provider, "mutate", unreadable_after_restore)
    assert env.compensate(req) == "RECOVERY_UNKNOWN"
    restore_receipt = env.provider.receipts[f"{req.operation_id}:restore"][3]
    assert restore_receipt != restart_receipt
    env.provider.readable = True
    env.allow(action="restore", decision="DENY")
    assert env.reconcile(req) == "SUCCEEDED"
    assert env.journal.get(req.operation_id)["provider_op"] == restore_receipt
    assert len(env.provider.effects) == 2
    assert env.reconcile(req) == "SUCCEEDED"
    assert env.journal.events(req.operation_id)[-1]["voodoo"] == "ALLOW"


def test_recovery_unknown_does_not_infer_success_without_restore_receipt(env, monkeypatch):
    req = broken_restart(env)
    env.grant("Ruku", "service_a", "restore")
    env.allow(action="restore")
    original = env.provider.mutate

    def unreadable_after_restore(*args):
        receipt = original(*args)
        env.provider.readable = False
        return receipt

    monkeypatch.setattr(env.provider, "mutate", unreadable_after_restore)
    assert env.compensate(req) == "RECOVERY_UNKNOWN"
    env.provider.readable = True
    env.provider.receipts.pop(f"{req.operation_id}:restore")
    assert env.reconcile(req) == "RECOVERY_UNKNOWN"
    assert env.journal.get(req.operation_id)["state"] == "RECOVERY_UNKNOWN"
    assert len(env.provider.effects) == 2
