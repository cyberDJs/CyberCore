"""Security regression tests for #113 SSH activation layout preflight."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nextcloud_r1_ssh_activation_preflight.py"
CANDIDATES = ROOT / "deploy" / "cybercore-exec-nextcloud-r1"


def load():
    spec = importlib.util.spec_from_file_location("cybercore_113_ssh_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SSHActivationLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load()
        cls.main = (
            "Include /etc/ssh/sshd_config.d/*.conf\n"
            "PermitRootLogin yes\n"
            "PasswordAuthentication yes\n"
            "Subsystem sftp /usr/lib/openssh/sftp-server\n"
        )
        cls.subsystem = (CANDIDATES / "sshd-subsystem-only.conf").read_text()
        cls.tail = (CANDIDATES / "sshd-match-tail.conf").read_text()

    def test_safe_split_candidate(self):
        self.assertEqual(self.mod.evaluate(self.main, self.subsystem, self.tail), [])

    def test_reject_early_match(self):
        injected = self.subsystem + "\nMatch User cybercore-exec\n"
        self.assertIn(
            "early included snippet must contain only exact Subsystem",
            self.mod.evaluate(self.main, injected, self.tail),
        )

    def test_reject_existing_main_match(self):
        issues = self.mod.evaluate(
            self.main + "\nMatch Address 10.0.0.0/8\n", self.subsystem, self.tail
        )
        self.assertTrue(any("already contains Match" in x for x in issues))

    def test_reject_duplicate_subsystem(self):
        issues = self.mod.evaluate(self.main + self.subsystem, self.subsystem, self.tail)
        self.assertTrue(any("already present" in x for x in issues))

    def test_reject_missing_force_command(self):
        bad = self.tail.replace("    ForceCommand ", "    # ForceCommand ")
        self.assertTrue(self.mod.evaluate(self.main, self.subsystem, bad))

    def test_reject_match_all(self):
        self.assertTrue(self.mod.evaluate(self.main, self.subsystem, self.tail + "Match all\\n"))

    def test_reject_noncanonical_target(self):
        self.assertTrue(
            self.mod.evaluate(
                self.main,
                self.subsystem.replace("cyberskills-vps", "tasks.cyberdjs.org"),
                self.tail,
            )
        )


if __name__ == "__main__":
    unittest.main()
