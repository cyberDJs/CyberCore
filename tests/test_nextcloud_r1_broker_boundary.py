"""Synthetic SO_PEERCRED and fd-bound approval tests for #113."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest

from cybercore.execution.nextcloud_r1_broker_boundary import (
    ACTION_TO_OPERATION,
    BoundaryConfig,
    FdBoundApprovalStore,
    Rejected,
    handle_accepted_client,
)


AUTH_DIGEST = hashlib.sha256(b"APPROVE-ISSUE-113-SYNTHETIC").hexdigest()


class BrokerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.approvals = self.root / "approvals"
        self.state = self.root / "state"
        self.approvals.mkdir(mode=0o700)
        self.state.mkdir(mode=0o700)
        self.uid = os.geteuid()
        self.now = 100
        self.boot_id = "boot-synthetic"
        self.config = BoundaryConfig(
            approval_dir=self.approvals,
            state_dir=self.state,
            trust_root=self.root,
            expected_peer_uid=self.uid,
            trusted_owner_uid=self.uid,
            plan_id="GH-113",
            plan_revision="2",
            source_identity="release-2f5c5a43",
            max_ttl_ns=100,
        )
        self.dispatched = []

    def manifest(self, **overrides):
        payload = {
            "schema_version": 1,
            "issue": 113,
            "target_id": "cyberskills-vps",
            "action": "transfer",
            "plan_id": "GH-113",
            "plan_revision": "2",
            "operation_id": "op-113-1",
            "source_identity": "release-2f5c5a43",
            "boot_id": self.boot_id,
            "issued_monotonic_ns": 90,
            "expires_monotonic_ns": 120,
            "authorization_reference_sha256": AUTH_DIGEST,
        }
        payload.update(overrides)
        return payload

    def write_manifest(self, payload=None, *, raw=None):
        path = self.approvals / "approval.json"
        if raw is None:
            raw = json.dumps(payload or self.manifest(), sort_keys=True).encode()
        path.write_bytes(raw)
        path.chmod(0o600)
        return path

    def store(self, *, monotonic=None, config=None):
        return FdBoundApprovalStore(
            config or self.config,
            boot_id_provider=lambda: self.boot_id,
            monotonic_ns=monotonic or (lambda: self.now),
        )

    def runner(self, argv):
        self.dispatched.append(argv)
        return 0

    def request_bytes(self, **overrides):
        payload = {"action": "transfer", "authorization_reference_sha256": AUTH_DIGEST}
        payload.update(overrides)
        return json.dumps(payload, separators=(",", ":")).encode()

    def invoke(self, store, *, raw=None, config=None, runner=None, socket_type=None):
        kind = socket.SOCK_SEQPACKET if socket_type is None else socket_type
        server, client = socket.socketpair(socket.AF_UNIX, kind)
        try:
            client.send(self.request_bytes() if raw is None else raw)
            returned = handle_accepted_client(
                server,
                config=config or self.config,
                approval_store=store,
                runner=runner or self.runner,
            )
            wire = json.loads(client.recv(4096).decode())
            self.assertEqual(wire, returned)
            return returned
        finally:
            server.close()
            client.close()

    def test_peercred_bound_exact_approval_dispatches_fixed_operation_once(self):
        self.write_manifest()
        with self.store() as store:
            response = self.invoke(store)
        self.assertTrue(response["ok"])
        self.assertEqual(response["status"], "DISPATCHED")
        self.assertEqual(len(self.dispatched), 1)
        self.assertEqual(
            self.dispatched[0],
            (
                "/usr/bin/systemctl",
                "start",
                "--no-block",
                "cybercore-nextcloud-r1-transfer.service",
            ),
        )
        prepared = next(self.state.glob("*.prepared.json")).read_text()
        self.assertIn("approval_manifest_sha256", prepared)
        self.assertNotIn("APPROVE-ISSUE-113-SYNTHETIC", prepared)

    def test_wrong_kernel_peer_uid_denied_before_approval_lookup(self):
        self.write_manifest()
        wrong = replace(self.config, expected_peer_uid=self.uid + 1)
        with self.store(config=wrong) as store:
            response = self.invoke(store, config=wrong)
        self.assertEqual(response, {"ok": False, "status": "DENIED"})
        self.assertFalse(self.dispatched)
        self.assertFalse(list(self.state.glob("*.prepared.json")))

    def test_stream_socket_is_denied(self):
        self.write_manifest()
        with self.store() as store:
            response = self.invoke(store, socket_type=socket.SOCK_STREAM)
        self.assertEqual(response, {"ok": False, "status": "DENIED"})
        self.assertFalse(self.dispatched)

    def test_request_schema_rejects_extra_and_duplicate_fields(self):
        self.write_manifest()
        extra = self.request_bytes(operation_id="caller-controlled")
        duplicate = (
            b'{"action":"transfer","action":"rollback",'
            b'"authorization_reference_sha256":"' + AUTH_DIGEST.encode() + b'"}'
        )
        with self.store() as store:
            self.assertEqual(self.invoke(store, raw=extra)["status"], "DENIED")
            self.assertEqual(self.invoke(store, raw=duplicate)["status"], "DENIED")
        self.assertFalse(self.dispatched)

    def test_manifest_symlink_and_unsafe_mode_are_denied(self):
        outside = self.root / "outside.json"
        outside.write_text(json.dumps(self.manifest()))
        outside.chmod(0o600)
        link = self.approvals / "approval.json"
        link.symlink_to(outside)
        with self.store() as store:
            self.assertEqual(self.invoke(store)["status"], "DENIED")
        link.unlink()
        path = self.write_manifest()
        path.chmod(0o622)
        with self.store() as store:
            self.assertEqual(self.invoke(store)["status"], "DENIED")
        self.assertFalse(self.dispatched)

    def test_symlinked_approval_directory_is_denied_at_store_open(self):
        real = self.root / "real-approvals"
        real.mkdir(mode=0o700)
        link = self.root / "linked-approvals"
        link.symlink_to(real, target_is_directory=True)
        config = replace(self.config, approval_dir=link)
        with self.assertRaises(Rejected):
            self.store(config=config)

    def test_wrong_boot_source_plan_or_reference_is_denied(self):
        cases = [
            {"boot_id": "other-boot"},
            {"source_identity": "other-release"},
            {"plan_revision": "3"},
            {"authorization_reference_sha256": hashlib.sha256(b"OTHER").hexdigest()},
        ]
        for index, override in enumerate(cases):
            with self.subTest(index=index):
                for path in self.approvals.glob("*"):
                    path.unlink()
                self.write_manifest(self.manifest(**override))
                with self.store() as store:
                    self.assertEqual(self.invoke(store)["status"], "DENIED")
        self.assertFalse(self.dispatched)

    def test_expired_and_overlong_monotonic_approval_are_denied(self):
        self.write_manifest(self.manifest(expires_monotonic_ns=100))
        with self.store() as store:
            self.assertEqual(self.invoke(store)["status"], "DENIED")
        (self.approvals / "approval.json").unlink()
        self.write_manifest(self.manifest(issued_monotonic_ns=1, expires_monotonic_ns=200))
        with self.store() as store:
            self.assertEqual(self.invoke(store)["status"], "DENIED")
        self.assertFalse(self.dispatched)

    def test_monotonic_regression_latches_store_fail_closed(self):
        samples = iter([100, 99, 101])
        self.write_manifest()
        with self.store(monotonic=lambda: next(samples)) as store:
            approval = store.load(
                action="transfer",
                authorization_reference_sha256=AUTH_DIGEST,
            )
            self.assertEqual(approval.request.operation, ACTION_TO_OPERATION["transfer"])
            with self.assertRaises(Rejected):
                store.sample_monotonic_ns()
            with self.assertRaises(Rejected):
                store.sample_monotonic_ns()

    def test_deadline_crossing_after_prepared_never_dispatches(self):
        samples = iter([100, 105, 121])
        self.write_manifest()
        with self.store(monotonic=lambda: next(samples)) as store:
            response = self.invoke(store)
        self.assertFalse(response["ok"])
        self.assertEqual(response["status"], "AUTHORIZATION_EXPIRED")
        self.assertFalse(self.dispatched)
        self.assertTrue(list(self.state.glob("*.prepared.json")))
        outcome = json.loads(next(self.state.glob("*.result.json")).read_text())
        self.assertEqual(outcome["state"], "AUTHORIZATION_EXPIRED")

    def test_dispatch_failure_and_unknown_are_not_reported_ok(self):
        self.write_manifest()
        with self.store() as store:
            failed = self.invoke(store, runner=lambda _argv: 7)
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["status"], "DISPATCH_FAILED")

        for path in self.state.glob("*"):
            path.unlink()
        (self.approvals / "approval.json").unlink()
        self.write_manifest(self.manifest(operation_id="op-113-2"))

        def crash(_argv):
            raise RuntimeError("synthetic runner failure")

        with self.store() as store:
            unknown = self.invoke(store, runner=crash)
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["status"], "DISPATCH_UNKNOWN")

    def test_manifest_duplicate_key_is_denied(self):
        raw = (
            b'{"schema_version":1,"schema_version":1,"issue":113,'
            b'"target_id":"cyberskills-vps","action":"transfer",'
            b'"plan_id":"GH-113","plan_revision":"2","operation_id":"op-113-1",'
            b'"source_identity":"release-2f5c5a43","boot_id":"boot-synthetic",'
            b'"issued_monotonic_ns":90,"expires_monotonic_ns":120,'
            b'"authorization_reference_sha256":"' + AUTH_DIGEST.encode() + b'"}'
        )
        self.write_manifest(raw=raw)
        with self.store() as store:
            self.assertEqual(self.invoke(store)["status"], "DENIED")
        self.assertFalse(self.dispatched)

    def test_oversized_request_is_denied(self):
        self.write_manifest()
        raw = b"x" * (self.config.max_request_bytes + 1)
        with self.store() as store:
            response = self.invoke(store, raw=raw)
        self.assertEqual(response["status"], "DENIED")
        self.assertFalse(self.dispatched)


if __name__ == "__main__":
    unittest.main()
