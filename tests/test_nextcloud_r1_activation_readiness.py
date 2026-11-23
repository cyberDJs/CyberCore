"""Isolated security regressions for #113 Phase-B activation readiness."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nextcloud_r1_activation_readiness.py"


def load():
    spec = importlib.util.spec_from_file_location("phase_b_readiness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActivationReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def fixture(self, tmp: Path):
        root = tmp / "release"
        root.mkdir(mode=0o700)
        files = {}
        for rel in self.m.EXPECTED_FILES:
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(rel.encode())
            dest.chmod(0o600)
            files[rel] = hashlib.sha256(dest.read_bytes()).hexdigest()
        manifest = {
            "schema_version": 1,
            "issue": 113,
            "target": "cyberskills-vps",
            "source_commit": self.m.SOURCE_SHA,
            "activation_performed": False,
            "files": files,
        }
        receipt = root / "stage-manifest.json"
        receipt.write_text(json.dumps(manifest))
        receipt.chmod(0o600)
        return root

    def test_valid_exact_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(Path(temp))
            result = self.m.assess(root, (), root_uid=0)
            self.assertEqual(result["status"], "READY_FOR_SEPARATE_ACTIVATION_DESIGN")
            self.assertEqual(result["release_files_verified"], 12)
            self.assertFalse(result["activation_performed"])

    def test_reject_nonroot(self):
        with self.assertRaisesRegex(ValueError, "root console"):
            self.m.assess(root_uid=1000)

    def test_reject_tampered_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(Path(temp))
            (root / "libexec/dispatcher.py").write_text("modified")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.m.assess(root, (), root_uid=0)

    def test_reject_extra_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(Path(temp))
            (root / "unexpected").write_text("unexpected")
            with self.assertRaisesRegex(ValueError, "unrecognized files"):
                self.m.assess(root, (), root_uid=0)

    def test_reject_manifest_identity_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.fixture(Path(temp))
            path = root / "stage-manifest.json"
            data = json.loads(path.read_text())
            data["source_commit"] = "0" * 40
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                self.m.assess(root, (), root_uid=0)

    def test_reject_symlinked_active_path(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.fixture(base)
            target = base / "target"
            target.write_text("original")
            active = base / "active"
            active.symlink_to(target)
            result = self.m.assess(root, (active,), root_uid=0)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["live_collisions"], [str(active)])

    def test_reject_existing_active_file(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.fixture(base)
            active = base / "active"
            active.write_text("not ours")
            result = self.m.assess(root, (active,), root_uid=0)
            self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
