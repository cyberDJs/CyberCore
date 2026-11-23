"""Read-only post-code gate regression tests for issue #113."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_post_code_readiness.py"


def load():
    spec = importlib.util.spec_from_file_location("post_code_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PostCodeReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_nonroot_cannot_inspect_private_receipt(self):
        with patch.object(self.m.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(ValueError, "root read-only"):
                self.m.assess()

    def test_clean_install_requires_separate_runtime_directories(self):
        def entries(path):
            return [SimpleNamespace(name=n) for n in self.m.MODULES[path.name]]

        def exists(path):
            return path not in self.m.RUNTIME_PATHS

        with (
            patch.object(self.m.os, "geteuid", return_value=0),
            patch.object(self.m.socket, "getfqdn", return_value=self.m.HOST),
            patch.object(self.m.pwd, "getpwnam", return_value=SimpleNamespace(
                pw_uid=995, pw_gid=987, pw_shell="/usr/sbin/nologin"
            )),
            patch.object(self.m.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=987)),
            patch.object(self.m, "issue_if_unsafe_node", return_value=None),
            patch.object(self.m, "inspect_acl", return_value=None),
            patch.object(self.m.Path, "iterdir", autospec=True, side_effect=entries),
            patch.object(self.m.Path, "exists", autospec=True, side_effect=exists),
            patch.object(self.m.Path, "is_symlink", return_value=False),
        ):
            result = self.m.assess()
        self.assertEqual(result["status"], "POST_CODE_READY_FOR_SEPARATE_ACTIVATION_DESIGN")
        self.assertEqual(result["verified_metadata_and_acl_files"], 8)
        self.assertEqual(len(result["missing_runtime_directories"]), 2)
        self.assertFalse(result["mutations_performed"])

    def test_mismatched_acl_fail_closed(self):
        with (
            patch.object(self.m.os, "geteuid", return_value=0),
            patch.object(self.m.socket, "getfqdn", return_value=self.m.HOST),
            patch.object(self.m.pwd, "getpwnam", return_value=SimpleNamespace(
                pw_uid=995, pw_gid=987, pw_shell="/usr/sbin/nologin"
            )),
            patch.object(self.m.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=987)),
            patch.object(self.m, "issue_if_unsafe_node", return_value=None),
            patch.object(self.m, "inspect_acl", return_value="acl_mismatch"),
            patch.object(self.m.Path, "iterdir", autospec=True,
                         side_effect=lambda path: [
                             SimpleNamespace(name=n) for n in self.m.MODULES[path.name]
                         ]),
            patch.object(self.m.Path, "exists", return_value=False),
            patch.object(self.m.Path, "is_symlink", return_value=False),
        ):
            result = self.m.assess()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("acl_mismatch", result["problems"])

    def test_missing_receipt_blocks(self):
        with (
            patch.object(self.m.os, "geteuid", return_value=0),
            patch.object(self.m.socket, "getfqdn", return_value=self.m.HOST),
            patch.object(self.m.pwd, "getpwnam", return_value=SimpleNamespace(
                pw_uid=995, pw_gid=987, pw_shell="/usr/sbin/nologin"
            )),
            patch.object(self.m.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=987)),
            patch.object(self.m, "issue_if_unsafe_node",
                         side_effect=lambda path, **kw: "missing:receipt"
                         if path == self.m.RECEIPT else None),
            patch.object(self.m, "inspect_acl", return_value=None),
            patch.object(self.m.Path, "iterdir", autospec=True,
                         side_effect=lambda path: [
                             SimpleNamespace(name=n) for n in self.m.MODULES[path.name]
                         ]),
            patch.object(self.m.Path, "exists", return_value=False),
            patch.object(self.m.Path, "is_symlink", return_value=False),
        ):
            result = self.m.assess()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("missing:receipt", result["problems"])


if __name__ == "__main__":
    unittest.main()
