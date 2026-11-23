"""Isolated tests for CyberCore #113 code-only transaction (never uses /usr/local)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_code_transaction.py"


def load():
    spec = importlib.util.spec_from_file_location("phase_b_transaction", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CodeOnlyTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def blobs(self):
        return {name: f"pinned:{name}".encode() for name in self.m.TARGETS}

    def patches(self):
        def test_safe_node(path, *, directory, mode):
            info = path.lstat()
            if directory != stat.S_ISDIR(info.st_mode):
                raise ValueError("unexpected node type")
            if stat.S_IMODE(info.st_mode) != mode:
                raise ValueError("unexpected node mode")

        return (
            mock.patch.object(self.m.os, "geteuid", return_value=0),
            mock.patch.object(self.m, "safe_root_parent"),
            mock.patch.object(self.m, "safe_node", side_effect=test_safe_node),
            mock.patch.object(self.m, "snapshot", return_value=self.blobs()),
            mock.patch.object(self.m, "exact_approval", return_value="test-approval"),
        )

    def test_apply_verify_rollback_no_activation(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            receipt = parent / "receipt.json"
            with self.patches()[0], self.patches()[1], self.patches()[2], self.patches()[3], self.patches()[4]:
                applied = self.m.apply(parent=parent, receipt=receipt, journal=parent / "intent.json")
                self.assertEqual(applied["status"], "CODE_ONLY_INSTALLED")
                self.assertFalse(applied["activation_performed"])
                self.assertEqual(self.m.verify(parent=parent, receipt=receipt, journal=parent / "intent.json")["status"], "CODE_ONLY_VERIFIED")
                rolled = self.m.rollback(parent=parent, receipt=receipt, journal=parent / "intent.json")
                self.assertEqual(rolled["status"], "CODE_ONLY_ROLLED_BACK")
                self.assertFalse(receipt.exists())
                for directory in self.m.DIRECTORIES:
                    self.assertFalse((parent / directory).exists())

    def test_reject_destination_collision_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            collision = parent / "cybercore-exec"
            collision.mkdir()
            marker = collision / "existing"
            marker.write_text("must survive")
            with self.patches()[0], self.patches()[1], self.patches()[2], self.patches()[3], self.patches()[4]:
                with self.assertRaisesRegex(ValueError, "collision"):
                    self.m.apply(parent=parent, receipt=parent / "receipt.json", journal=parent / "intent.json")
            self.assertEqual(marker.read_text(), "must survive")

    def test_reject_mutated_deployment_before_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            receipt = parent / "receipt.json"
            with self.patches()[0], self.patches()[1], self.patches()[2], self.patches()[3], self.patches()[4]:
                self.m.apply(parent=parent, receipt=receipt, journal=parent / "intent.json")
                file = parent / "cybercore-exec" / "dispatcher.py"
                file.write_text("changed")
                with self.assertRaisesRegex(ValueError, "differs"):
                    self.m.rollback(parent=parent, receipt=receipt, journal=parent / "intent.json")
                self.assertTrue(file.exists())
                self.assertTrue(receipt.exists())

    def test_interrupted_intent_blocks_apply_and_requires_reconcile(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            receipt = parent / "receipt.json"
            journal = parent / "intent.json"
            with self.patches()[0], self.patches()[1], self.patches()[2], self.patches()[3], self.patches()[4]:
                hashes = {
                    relative: self.m.sha(self.blobs()[original])
                    for original, relative in self.m.TARGETS.items()
                }
                self.m.write_root_json(journal, {
                    "issue": 113, "source_commit": self.m.SOURCE_SHA,
                    "status": "CODE_ONLY_IN_PROGRESS", "file_sha256": hashes,
                    "approval_id": "test-approval"
                })
                with self.assertRaisesRegex(ValueError, "pending intent"):
                    self.m.apply(parent=parent, receipt=receipt, journal=journal)
                result = self.m.reconcile(parent=parent, receipt=receipt, journal=journal)
                self.assertEqual(result["status"], "CODE_ONLY_INTENT_RECONCILED")
                self.assertFalse(journal.exists())

    def test_no_root_no_apply(self):
        with mock.patch.object(self.m.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(ValueError, "root"):
                self.m.apply()

    def test_model_plan_does_not_mutate(self):
        self.assertEqual(self.m.main.__name__, "main")
        self.assertEqual(len(self.m.TARGETS), 8)


if __name__ == "__main__":
    unittest.main()
