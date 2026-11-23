"""Regression checks for CyberCore #113 Polkit authorization boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_privilege_bypass_preflight.py"


def load():
    spec = importlib.util.spec_from_file_location("polkit_bypass_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PolkitBypassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_live_candidate_direct_unit_start_is_blocked(self):
        result = self.m.assess(
            self.m.POLICY.read_text(),
            self.m.OPERATIONS.read_text(),
        )
        self.assertEqual(result["status"], "BLOCKED_DIRECT_UNIT_START")
        self.assertTrue(result["direct_privileged_start_grant_detected"])
        self.assertFalse(result["activation_approved"])
        self.assertFalse(result["activation_performed"])

    def test_comment_cannot_fake_direct_grant(self):
        text = (
            "// polkit.Result.YES org.freedesktop.systemd1.manage-units\n"
            "// cybercore-exec cybercore-nextcloud-r1-transfer.service\n"
            "// cybercore-nextcloud-r1-rollback.service\n"
            "polkit.Result.NOT_HANDLED;"
        )
        result = self.m.assess(text, self.m.OPERATIONS.read_text())
        self.assertFalse(result["direct_privileged_start_grant_detected"])
        self.assertEqual(result["status"], "STATIC_CANDIDATE_REQUIRES_RUNTIME_PROOF")

    def test_missing_governed_operation_mapping_blocks(self):
        result = self.m.assess("polkit.Result.NOT_HANDLED;", "no operations")
        self.assertEqual(result["status"], "BLOCKED_DIRECT_UNIT_START")
        self.assertIn("expected_governed_operation_mapping_missing", result["concerns"])

    def test_no_static_pass_counts_as_runtime_proof(self):
        result = self.m.assess(
            "polkit.Result.NOT_HANDLED;",
            self.m.OPERATIONS.read_text(),
        )
        self.assertFalse(result["runtime_denial_verified"])
        self.assertFalse(result["activation_approved"])


if __name__ == "__main__":
    unittest.main()
