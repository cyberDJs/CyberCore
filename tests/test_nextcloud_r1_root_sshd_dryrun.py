"""Focused offline SSH activation checks for CyberCore issue #113."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nextcloud_r1_root_sshd_dryrun.py"
CANDIDATES = ROOT / "deploy" / "cybercore-exec-nextcloud-r1"


def load():
    spec = importlib.util.spec_from_file_location("cybercore_113_root_ssh", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RootOfflineSSHPreflightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load()
        cls.primary = (
            "Include /etc/ssh/sshd_config.d/*.conf\n"
            "PermitRootLogin yes\n"
            "PasswordAuthentication yes\n"
            "Subsystem sftp /usr/lib/openssh/sftp-server\n"
        )
        cls.includes = {"50-cloud-init.conf": "PasswordAuthentication yes\n"}
        cls.subsystem = (CANDIDATES / "sshd-subsystem-only.conf").read_text()
        cls.tail = (CANDIDATES / "sshd-match-tail.conf").read_text()

    def test_matching_templates_and_realistic_include(self):
        self.module.check_layout(
            self.primary, self.includes, self.subsystem, self.tail
        )

    def test_reject_existing_match_inside_early_include(self):
        includes = {"50-cloud-init.conf": "Match User root\nPermitTTY yes\n"}
        with self.assertRaisesRegex(ValueError, "unreviewed nested"):
            self.module.check_layout(
                self.primary, includes, self.subsystem, self.tail
            )

    def test_reject_duplicate_subsystem(self):
        with self.assertRaisesRegex(ValueError, "already installed"):
            self.module.check_layout(
                self.primary + self.subsystem, self.includes, self.subsystem, self.tail
            )

    def test_reject_extra_include(self):
        with self.assertRaisesRegex(ValueError, "additional primary Include"):
            self.module.check_layout(
                self.primary + "Include /another/*.conf\n",
                self.includes, self.subsystem, self.tail
            )

    def test_reject_modified_force_command(self):
        tail = self.tail.replace("cyberskills-vps", "tasks.cyberdjs.org")
        with self.assertRaisesRegex(ValueError, "deviates"):
            self.module.check_layout(
                self.primary, self.includes, self.subsystem, tail
            )

    def test_reject_early_match_user(self):
        with self.assertRaisesRegex(ValueError, "not exact"):
            self.module.check_layout(
                self.primary, self.includes,
                self.subsystem + "Match User cybercore-exec\n",
                self.tail,
            )

    def test_non_root_cannot_stage_even_readonly_root_configs(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            main = base / "main"
            main.write_text(self.primary)
            directory = base / "includes"
            directory.mkdir()
            include = directory / "50-cloud-init.conf"
            include.write_text(self.includes["50-cloud-init.conf"])
            candidate = base / "subsystem"
            candidate.write_text(self.subsystem)
            tail = base / "tail"
            tail.write_text(self.tail)
            with mock.patch.object(self.module.os, "geteuid", return_value=1000):
                with self.assertRaisesRegex(ValueError, "root is required"):
                    self.module.preflight(
                        main, directory, candidate, tail, "127.0.0.1", "/usr/sbin/sshd"
                    )

    def test_effective_retains_multiple_subsystems(self):
        result = mock.Mock()
        result.stdout = (
            "permitrootlogin yes\nsubsystem cybercore-exec /bin/python3 x\n"
            "subsystem sftp /usr/lib/sftp-server\n"
        )
        with mock.patch.object(self.module.subprocess, "run", return_value=result):
            effective = self.module.effective(
                "/usr/sbin/sshd", Path("/tmp/proposal"), "root", "127.0.0.1"
            )
        self.assertIn("cybercore-exec", effective["subsystem"])
        self.assertIn("sftp", effective["subsystem"])


if __name__ == "__main__":
    unittest.main()
