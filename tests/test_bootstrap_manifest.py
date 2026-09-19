from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from cybercore.execution.server.operations import SUPPORTED_SERVER_OPERATIONS


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy/cybercore-exec"


def load_deploy_module(name: str):
    path = DEPLOY / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cybercore_exec_{name}", path)
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
    module = load_deploy_module("install")
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


def test_operation_map_uses_only_fixed_systemd_units() -> None:
    operations = (ROOT / "src/cybercore/execution/server/operations.py").read_text()
    assert "/usr/bin/sudo" not in operations
    assert "systemd-run" not in operations
    assert "/usr/bin/systemctl" in operations
    assert "cybercore-vikunja-backup-install.service" in operations
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup-install" not in operations


def test_backup_installer_unit_has_fixed_root_execstart() -> None:
    text = (DEPLOY / "cybercore-vikunja-backup-install.service").read_text()
    assert "Type=oneshot" in text
    assert "User=root" in text
    assert "Group=root" in text
    assert "ExecStart=/usr/local/libexec/cybercore-exec/vikunja-backup-install" in text
    assert "systemd-run" not in text


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


def test_bootstrap_manifest_installs_static_unit_and_reloads_systemd() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    actions = {action.action_id: action for action in manifest}

    unit = actions["backup-installer-unit"]
    assert unit.destination == "/etc/systemd/system/cybercore-vikunja-backup-install.service"
    assert unit.source == "deploy/cybercore-exec/cybercore-vikunja-backup-install.service"
    assert unit.mode == "0644"
    assert actions["systemd-reload"].action_type.value == "RELOAD_SYSTEMD"


def test_rollback_revokes_policy_helper_and_static_unit() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    actions = {action.action_id: action for action in manifest}

    assert actions["remove-privilege-policy"].target == (
        "/etc/polkit-1/rules.d/60-cybercore-exec.rules"
    )
    assert actions["remove-backup-installer"].target == (
        "/usr/local/libexec/cybercore-exec/vikunja-backup-install"
    )
    assert actions["remove-backup-installer-unit"].target == (
        "/etc/systemd/system/cybercore-vikunja-backup-install.service"
    )
    assert actions["systemd-reload"].action_type.value == "RELOAD_SYSTEMD"


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text
