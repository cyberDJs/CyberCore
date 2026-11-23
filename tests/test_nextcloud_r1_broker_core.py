"""Synthetic denial and crash-fence tests for inert #113 broker core."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from cybercore.execution import nextcloud_r1_broker_core as broker_core
from cybercore.execution.nextcloud_r1_broker_core import (
    Request,
    Rejected,
    broker_once,
    ALLOWED,
)
from cybercore.execution.server import operations as server_operations


@dataclass
class Decision:
    authorized: bool


class FakeVerifier:
    def __init__(self, allowed: bool = True):
        self.allowed = allowed
        self.calls = 0

    def verify(self, **kwargs):
        self.calls += 1
        return Decision(self.allowed)


def request(operation: str = "nextcloud.r1.offhost.transfer", operation_id: str = "op-1"):
    return Request(operation_id, operation, "cyberskills-vps", "plan-a", "1", "synthetic-ref")


class BrokerCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.uid = os.geteuid()
        self.dispatched = []
        self.verifier = FakeVerifier()

    def invoke(self, req=None, *, peer_uid=995, expected_peer_uid=995, verifier=None, runner=None):
        return broker_once(
            req or request(),
            peer_uid=peer_uid,
            expected_peer_uid=expected_peer_uid,
            verifier=self.verifier if verifier is None else verifier,
            state_dir=self.state,
            runner=runner or self.runner,
            owner_uid=self.uid,
        )

    def runner(self, argv):
        self.dispatched.append(argv)
        return 0

    def test_exact_authorized_transfer_runs_once(self):
        response = self.invoke()
        self.assertEqual(response["status"], "DISPATCHED")
        self.assertEqual(self.dispatched, [ALLOWED["nextcloud.r1.offhost.transfer"]])
        self.assertTrue(list(self.state.glob("*.prepared.json")))
        self.assertTrue(list(self.state.glob("*.result.json")))
        self.assertFalse(response["unit_start_proven"])
        with self.assertRaisesRegex(Rejected, "already been prepared"):
            self.invoke()
        self.assertEqual(len(self.dispatched), 1)

    def test_unauthorized_or_expired_approval_denied_before_dispatch(self):
        with self.assertRaisesRegex(Rejected, "no valid exact action"):
            self.invoke(verifier=FakeVerifier(False))
        self.assertFalse(self.dispatched)
        self.assertFalse(list(self.state.glob("*.prepared.json")))

    def test_wrong_uid_rejected_without_verifier(self):
        with self.assertRaisesRegex(Rejected, "peer identity"):
            self.invoke(peer_uid=996)
        self.assertEqual(self.verifier.calls, 0)
        self.assertFalse(self.dispatched)

    def test_wrong_target_or_operation_rejected(self):
        invalid = Request("id", "unrelated.command", "cyberskills-vps", "plan", "1", "ref")
        with self.assertRaisesRegex(Rejected, "unsupported"):
            self.invoke(invalid)
        target = Request(
            "id", "nextcloud.r1.offhost.rollback", "tasks.cyberdjs.org", "plan", "1", "ref"
        )
        with self.assertRaisesRegex(Rejected, "unsupported"):
            self.invoke(target)
        self.assertFalse(self.dispatched)

    def test_prepared_crash_marker_blocks_every_retry(self):
        prepared = self.invoke()
        self.assertEqual(prepared["status"], "DISPATCHED")
        for path in self.state.glob("*.result.json"):
            path.unlink()
        with self.assertRaisesRegex(Rejected, "already been prepared"):
            self.invoke()
        self.assertEqual(len(self.dispatched), 1)

    def test_dispatch_failure_is_nonretryable(self):
        result = self.invoke(runner=lambda argv: 7)
        self.assertEqual(result["status"], "DISPATCH_FAILED")
        with self.assertRaisesRegex(Rejected, "already been prepared"):
            self.invoke()

    def test_dispatch_exception_is_nonretryable(self):
        def crash(_argv):
            raise RuntimeError("synthetic")

        result = self.invoke(runner=crash)
        self.assertEqual(result["status"], "DISPATCH_UNKNOWN")
        with self.assertRaisesRegex(Rejected, "already been prepared"):
            self.invoke()

    def test_insecure_state_directory_refused(self):
        self.state.chmod(0o777)
        with self.assertRaisesRegex(Rejected, "unsafe broker state"):
            self.invoke()
        self.assertFalse(self.dispatched)

    def test_collision_blocks_without_clobber(self):
        path = self.state / "broker.lock"
        path.symlink_to("/dev/null")
        with self.assertRaises(OSError):
            self.invoke()
        self.assertFalse(self.dispatched)

    def test_owner_check_is_required(self):
        with patch("cybercore.execution.nextcloud_r1_broker_core.os.geteuid", return_value=100000):
            with self.assertRaisesRegex(Rejected, "trusted state owner"):
                self.invoke()
        self.assertFalse(self.dispatched)

    def test_different_ids_require_new_independent_verification(self):
        self.invoke()
        self.invoke(request(operation_id="op-2"))
        self.assertEqual(self.verifier.calls, 2)
        self.assertEqual(len(self.dispatched), 2)

    def test_state_writes_retry_partial_os_write_until_complete(self):
        real_write = os.write

        def partial_write(fd, raw):
            return real_write(fd, raw[: max(1, min(7, len(raw)))])

        with patch(
            "cybercore.execution.nextcloud_r1_broker_core.os.write",
            side_effect=partial_write,
        ):
            result = self.invoke()
        self.assertEqual(result["status"], "DISPATCHED")
        prepared = next(self.state.glob("*.prepared.json"))
        outcome = next(self.state.glob("*.result.json"))
        self.assertEqual(json.loads(prepared.read_text())["state"], "PREPARED")
        self.assertEqual(json.loads(outcome.read_text())["state"], "DISPATCHED")

    def test_lock_descriptor_is_close_on_exec(self):
        fd = broker_core._lock(self.state / "broker.lock", owner_uid=self.uid)
        try:
            flags = fcntl.fcntl(fd, fcntl.F_GETFD)
            self.assertTrue(flags & fcntl.FD_CLOEXEC)
        finally:
            os.close(fd)

    def test_fixed_argv_matches_canonical_server_operation_specs(self):
        for operation, argv in ALLOWED.items():
            self.assertEqual(argv, server_operations._OPERATION_SPECS[operation].argv)

    def test_concurrent_duplicate_dispatches_at_most_once(self):
        entered = threading.Event()
        release = threading.Event()
        results = []
        errors = []

        def runner(argv):
            self.dispatched.append(argv)
            entered.set()
            release.wait(timeout=2)
            return 0

        def invoke():
            try:
                results.append(self.invoke(runner=runner))
            except Exception as exc:
                errors.append(exc)

        first = threading.Thread(target=invoke)
        second = threading.Thread(target=invoke)
        first.start()
        self.assertTrue(entered.wait(timeout=2))
        second.start()
        release.set()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertEqual(len(self.dispatched), 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "DISPATCHED")
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], Rejected)
        self.assertIn("already been prepared", str(errors[0]))

    def test_rollback_fixed_argv(self):
        outcome = self.invoke(request("nextcloud.r1.offhost.rollback"))
        self.assertEqual(outcome["status"], "DISPATCHED")
        self.assertEqual(self.dispatched, [ALLOWED["nextcloud.r1.offhost.rollback"]])


if __name__ == "__main__":
    unittest.main()
