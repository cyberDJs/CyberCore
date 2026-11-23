"""#113 inert bootstrap safety regression tests (never touch live paths)."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_inert_bootstrap.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("inert_bootstrap_113", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InertBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.module = load_candidate()
        self.base = Path(self.work.name) / "root-only-stage"
        self.files = {
            "libexec/dispatcher.py": b"no live dispatcher\n",
            "candidate/sshd.conf": b"not a live sshd snippet\n",
        }
        self.manifest = self.module.expected_manifest(self.files)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(self.module, "BASE", self.base))
        self.stack.enter_context(mock.patch.object(self.module, "PREFIX", self.base / "releases"))
        self.stack.enter_context(
            mock.patch.object(self.module, "RELEASE", self.base / "releases" / self.module.SOURCE_SHA)
        )
        self.stack.enter_context(mock.patch.object(self.module, "OWNER_UID", os.getuid()))
        self.stack.enter_context(mock.patch.object(self.module, "safe_parent", lambda: None))

    def stage(self):
        with mock.patch.object(self.module.os, "geteuid", return_value=0):
            self.module.atomic_stage(self.files, self.manifest)

    def test_stage_verify_and_remove_only_inert_release(self):
        self.stage()
        self.module.inspect_release(self.manifest)
        with mock.patch.object(self.module.os, "geteuid", return_value=0):
            self.module.rollback(self.manifest)
        self.assertFalse(self.module.RELEASE.exists())
        self.assertTrue(self.base.exists())

    def test_repeat_stage_fails_without_overwrite(self):
        self.stage()
        with mock.patch.object(self.module.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                self.module.atomic_stage(self.files, self.manifest)

    def test_tamper_blocks_removal(self):
        self.stage()
        target = self.module.RELEASE / "libexec" / "dispatcher.py"
        target.write_bytes(b"modified by someone else")
        with mock.patch.object(self.module.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "contents drift"):
                self.module.rollback(self.manifest)
        self.assertTrue(target.exists())

    def test_unknown_file_blocks_removal(self):
        self.stage()
        unknown = self.module.RELEASE / "foreign.txt"
        unknown.write_text("preserve me")
        with mock.patch.object(self.module.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(RuntimeError, "unexpected managed path"):
                self.module.rollback(self.manifest)
        self.assertTrue(unknown.exists())

    def test_apply_requires_root(self):
        with mock.patch.object(self.module.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(RuntimeError, "requires root"):
                self.module.atomic_stage(self.files, self.manifest)
        self.assertFalse(self.module.RELEASE.exists())

    def test_untrusted_source_sha_rejected(self):
        with mock.patch.object(self.module, "git_sha", return_value="incorrect"):
            with self.assertRaisesRegex(RuntimeError, "source tree SHA"):
                self.module.snapshot(Path(self.work.name))

    def test_action_bound_short_lived_approval(self):
        approval_dir = Path(self.work.name) / "approvals"
        approval_dir.mkdir(mode=0o700)
        approval = approval_dir / "bootstrap-stage-113.json"
        now = datetime.now(timezone.utc)
        record = {
            "schema_version": 1,
            "issue": 113,
            "target": self.module.TARGET,
            "source_commit": self.module.SOURCE_SHA,
            "action": "stage-inert",
            "approval_id": "test-approval-do-not-use",
            "issued_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        }
        approval.write_text(json.dumps(record))
        approval.chmod(0o600)
        with (
            mock.patch.object(self.module, "APPROVAL_PATH", approval),
            mock.patch.object(self.module, "APPROVAL_OWNER_UID", os.getuid()),
        ):
            self.assertEqual(self.module.require_fresh_approval("stage-inert"), record["approval_id"])
            with self.assertRaisesRegex(RuntimeError, "exact action"):
                self.module.require_fresh_approval("rollback-inert")
            record["expires_at"] = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")
            approval.write_text(json.dumps(record))
            with self.assertRaisesRegex(RuntimeError, "lifetime"):
                self.module.require_fresh_approval("stage-inert")


if __name__ == "__main__":
    unittest.main()
