"""Regression guard: installed Nextcloud R1 rollback can import standalone.

The systemd unit launches rollback.py from a flat libexec directory, without
CyberCore installed in the target interpreter's site-packages.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "src" / "cybercore" / "execution"


class NextcloudR1StandaloneRollbackTest(unittest.TestCase):
    def test_standalone_libexec_import(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw)
            shutil.copyfile(EXECUTION / "nextcloud_r1_transfer.py", target / "transfer.py")
            shutil.copyfile(EXECUTION / "nextcloud_r1_rollback.py", target / "rollback.py")
            # -I excludes PYTHONPATH and user site packages. No rollback main().
            result = subprocess.run(
                [sys.executable, "-I", "-c",
                 "import sys; sys.path.insert(0, sys.argv[1]); "
                 "import rollback; assert rollback.PRIVATE_KEY.name == 'source_ed25519'",
                 str(target)],
                cwd=target,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
