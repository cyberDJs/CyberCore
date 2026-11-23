"""CyberCore #113 identity preflight: read-only and negative tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_identity_preflight.py"


def load():
    spec = importlib.util.spec_from_file_location("identity_preflight_113", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IdentityPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def user(self, **overrides):
        base = dict(pw_uid=995, pw_gid=995, pw_shell="/usr/sbin/nologin",
                    pw_passwd="x", pw_dir="/nonexistent/cybercore-exec")
        base.update(overrides)
        return SimpleNamespace(**base)

    def group(self, **overrides):
        base = dict(gr_gid=995)
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_both_absent_separate_root_gate(self):
        state, violations = self.m.evaluate_identity(None, None, {})
        self.assertEqual(state, "IDENTITY_ABSENT_READY_FOR_SEPARATE_ROOT_PROVISIONING")
        self.assertEqual(violations, [])

    def test_partial_collision_fails_closed(self):
        state, violations = self.m.evaluate_identity(self.user(), None, {})
        self.assertEqual(state, "BLOCKED")
        self.assertIn("partial user/group collision", violations)

    def test_valid_noninteractive_identity(self):
        state, violations = self.m.evaluate_identity(self.user(), self.group(), {})
        self.assertEqual(state, "IDENTITY_PRESENT_RESTRICTED")
        self.assertFalse(violations)

    def test_reject_interactive_shell(self):
        state, violations = self.m.evaluate_identity(
            self.user(pw_shell="/bin/bash"), self.group(), {}
        )
        self.assertEqual(state, "BLOCKED")
        self.assertTrue(any("shell" in v for v in violations))

    def test_reject_group_mismatch(self):
        state, violations = self.m.evaluate_identity(
            self.user(pw_gid=991), self.group(), {}
        )
        self.assertEqual(state, "BLOCKED")
        self.assertTrue(any("primary" in v for v in violations))

    def test_reject_privileged_supplementary_group(self):
        state, violations = self.m.evaluate_identity(
            self.user(), self.group(), {"sudo": {"cybercore-exec"}}
        )
        self.assertEqual(state, "BLOCKED")
        self.assertTrue(any("supplementary" in v for v in violations))

    def test_wrong_host_blocks_without_mutation(self):
        with (
            patch.object(self.m.socket, "getfqdn", return_value="wrong.host"),
            patch.object(self.m, "check_directory", return_value=None),
            patch.object(self.m, "find_user", return_value=None),
            patch.object(self.m, "find_group", return_value=None),
            patch.object(self.m.grp, "getgrall", return_value=[]),
            patch.object(self.m.Path, "exists", return_value=False),
            patch.object(self.m.Path, "is_symlink", return_value=False),
        ):
            result = self.m.preflight()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertFalse(result["commands_executed"])
        self.assertFalse(result["identity_created"])

    def test_path_collision_blocks(self):
        with (
            patch.object(self.m.socket, "getfqdn", return_value=self.m.HOST),
            patch.object(self.m, "check_directory", return_value=None),
            patch.object(self.m, "find_user", return_value=None),
            patch.object(self.m, "find_group", return_value=None),
            patch.object(self.m.grp, "getgrall", return_value=[]),
            patch.object(self.m.Path, "exists", return_value=True),
        ):
            result = self.m.preflight()
        self.assertEqual(result["state"], "BLOCKED")
        self.assertTrue(any("colliding path" in v for v in result["violations"]))


if __name__ == "__main__":
    unittest.main()
