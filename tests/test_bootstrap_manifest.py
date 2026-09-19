from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from cybercore.execution.server.operations import SUPPORTED_SERVER_OPERATIONS


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy/cybercore-exec"


def load_install_module():
    path = DEPLOY / "install.py"
    spec = importlib.util.spec_from_file_location("cybercore_exec_install", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_operation_surface_is_exact() -> None:
    assert SUPPORTED_SERVER_OPERATIONS == {
        "vikunja.backup.install",
        "vikunja.backup.run",
        "vikunja.backup.status",
        "vikunja.health.verify",
    }


def test_sshd_snippet_forces_dispatcher_and_resets_match_scope() -> None:
    text = (DEPLOY / "cybercore-exec.subsystem.conf").read_text()
    assert (
        "Subsystem cybercore-exec /usr/bin/python3 /usr/local/libexec/cybercore-exec/dispatcher.py"
    ) in text
    assert ("ForceCommand /usr/bin/python3 /usr/local/libexec/cybercore-exec/dispatcher.py") in text
    assert "PermitTTY no" in text
    assert "AllowTcpForwarding no" in text
    assert text.rstrip().endswith("Match all")


def test_privilege_policy_is_polkit_and_exact() -> None:
    text = (DEPLOY / "cybercore-exec.policy").read_text()
    assert "org.freedesktop.systemd1.manage-units" in text
    assert 'unit === "vikunja-backup.service"' in text
    assert 'unit === "cybercore-vikunja-backup-install.service"' in text
    assert 'verb !== "start"' in text
    assert "NOPASSWD" not in text
    assert "/usr/bin/sudo" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_bootstrap_installs_every_fixed_helper_source() -> None:
    module = load_install_module()
    manifest = module.build_install_manifest()
    server_files = {
        action.destination: action.source
        for action in manifest
        if action.action_type.value == "INSTALL_SERVER_FILE"
    }
    assert server_files["/usr/local/libexec/cybercore-exec/vikunja-backup-install"] == (
        "deploy/cybercore-exec/vikunja-backup-install"
    )
    for source in server_files.values():
        assert (ROOT / source).is_file(), source


def test_operation_map_references_only_deployed_helper() -> None:
    operations = (ROOT / "src/cybercore/execution/server/operations.py").read_text()
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup-install" in operations
    assert "/usr/bin/sudo" not in operations
    assert "systemd-run" in operations
    assert "cybercore-vikunja-backup-install" in operations


def test_backup_installer_is_fixed_and_shell_free() -> None:
    text = (DEPLOY / "vikunja-backup-install").read_text()
    assert "/opt/vikunja" in text
    assert "/opt/backups/vikunja" in text
    assert "vikunja-backup.service" in text
    assert "vikunja-backup.timer" in text
    assert "RETENTION_DAYS = 14" in text
    assert "shell=False" in text
    assert "shell=True" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text
