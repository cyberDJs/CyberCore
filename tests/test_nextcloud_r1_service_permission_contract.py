"""Tests for the synthetic CyberCore #113 Phase-B permission contract."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nextcloud_r1_service_permission_contract.py"


def load():
    spec = importlib.util.spec_from_file_location("phase_b_permission", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PermissionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def replaced(self, name: str, **kwargs):
        return tuple(replace(n, **kwargs) if n.name == name else n for n in self.m.PLAN)

    def test_valid_proposed_contract(self):
        result = self.m.validate()
        self.assertEqual(result["status"], "PROPOSED_PERMISSION_CONTRACT_VERIFIED")
        self.assertFalse(result["activation_performed"])
        self.assertFalse(result["production_paths_inspected"])

    def test_unprivileged_user_can_read_manifest(self):
        nodes = {x.name: x for x in self.m.PLAN}
        user = self.m.SERVICE_UID
        group = frozenset({self.m.SERVICE_GID})
        self.assertTrue(self.m.can(nodes["/etc/cybercore-exec/approvals"], user, group, 1))
        self.assertTrue(
            self.m.can(nodes["/etc/cybercore-exec/approvals/nextcloud-r1.json"], user, group, 4)
        )

    def test_unprivileged_user_cannot_write_manifest(self):
        manifest = next(
            n for n in self.m.PLAN if n.name.endswith("/nextcloud-r1.json")
        )
        self.assertFalse(
            self.m.can(manifest, self.m.SERVICE_UID, frozenset({self.m.SERVICE_GID}), 2)
        )

    def test_outsider_cannot_read_manifest(self):
        manifest = next(
            n for n in self.m.PLAN if n.name.endswith("/nextcloud-r1.json")
        )
        self.assertFalse(
            self.m.can(manifest, self.m.OTHER_UID, frozenset({self.m.OTHER_GID}), 4)
        )

    def test_deny_group_writable_approval_directory(self):
        nodes = self.replaced("/etc/cybercore-exec/approvals", mode=0o770)
        with self.assertRaisesRegex(ValueError, "contract drift"):
            self.m.validate(nodes)

    def test_deny_world_readable_manifest(self):
        nodes = self.replaced(
            "/etc/cybercore-exec/approvals/nextcloud-r1.json", mode=0o644
        )
        with self.assertRaisesRegex(ValueError, "contract drift"):
            self.m.validate(nodes)

    def test_deny_service_owned_dispatcher(self):
        nodes = self.replaced(
            "/usr/local/libexec/cybercore-exec/dispatcher.py", uid=self.m.SERVICE_UID
        )
        with self.assertRaisesRegex(ValueError, "contract drift"):
            self.m.validate(nodes)

    def test_deny_missing_manifest(self):
        nodes = tuple(n for n in self.m.PLAN if not n.name.endswith("/nextcloud-r1.json"))
        with self.assertRaisesRegex(ValueError, "missing"):
            self.m.validate(nodes)

    def test_deny_duplicate_path(self):
        nodes = self.m.PLAN + (self.m.PLAN[0],)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.m.validate(nodes)


if __name__ == "__main__":
    unittest.main()
