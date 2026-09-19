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


def test_privilege_policy_allows_only_preinstalled_static_wrappers() -> None:
    text = (DEPLOY / "cybercore-exec.policy").read_text()
    assert "org.freedesktop.systemd1.manage-units" in text
    assert 'unit === "cybercore-vikunja-backup-install.service"' in text
    assert 'unit === "cybercore-vikunja-backup-run.service"' in text
    assert 'unit === "vikunja-backup.service"' not in text
    assert 'verb !== "start"' in text
    assert "NOPASSWD" not in text
    assert "/usr/bin/sudo" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_bootstrap_installs_static_wrappers_before_privilege_policy() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    index = {action.action_id: position for position, action in enumerate(manifest)}
    by_id = {action.action_id: action for action in manifest}

    for action_id in ("vikunja-backup-install-unit", "vikunja-backup-run-unit"):
        action = by_id[action_id]
        assert action.action_type.value == "INSTALL_SYSTEMD_UNIT"
        assert (ROOT / action.source).is_file()
        assert action.mode == "0644"
        assert action.owner == "root"
        assert action.group == "root"
        assert index[action_id] < index["systemd-reload"]

    assert index["systemd-reload"] < index["privilege-policy"]


def test_bootstrap_installs_every_fixed_helper_source_with_private_mode() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    server_files = {
        action.destination: action
        for action in manifest
        if action.action_type.value == "INSTALL_SERVER_FILE"
    }
    assert server_files["/usr/local/libexec/cybercore-exec/authorization.py"].source == (
        "src/cybercore/execution/authorization.py"
    )
    helper = server_files["/usr/local/libexec/cybercore-exec/vikunja-backup-install"]
    assert helper.source == "deploy/cybercore-exec/vikunja-backup-install"
    assert helper.mode == "0700"
    for action in server_files.values():
        assert action.owner == "root"
        assert action.group == "root"
        assert (ROOT / action.source).is_file(), action.source


def test_privileged_config_installs_are_explicitly_root_owned() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    privileged_types = {
        "INSTALL_SYSTEMD_UNIT",
        "INSTALL_SSHD_CONFIG",
        "INSTALL_PRIVILEGE_POLICY",
    }
    privileged = [action for action in manifest if action.action_type.value in privileged_types]
    assert privileged
    assert all(action.owner == "root" and action.group == "root" for action in privileged)


def test_operation_map_uses_only_static_wrapper_units() -> None:
    operations = (ROOT / "src/cybercore/execution/server/operations.py").read_text()
    assert "systemd-run" not in operations
    assert "/usr/bin/sudo" not in operations
    assert '"cybercore-vikunja-backup-install.service"' in operations
    assert '"cybercore-vikunja-backup-run.service"' in operations


def test_backup_installer_is_fixed_shell_free_and_private() -> None:
    text = (DEPLOY / "vikunja-backup-install").read_text()
    assert "/opt/vikunja" in text
    assert "/opt/backups/vikunja" in text
    assert "vikunja-backup.service" in text
    assert "vikunja-backup.timer" in text
    assert "RETENTION_DAYS = 14" in text
    assert "write_exact(BACKUP_SCRIPT, BACKUP_SCRIPT_TEXT, 0o700)" in text
    assert "shell=False" in text
    assert "shell=True" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_rollback_revokes_policy_and_static_wrappers_symmetrically() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    targets = {action.target for action in manifest if action.target}

    assert manifest[0].action_id == "remove-privilege-policy"
    assert "/etc/polkit-1/rules.d/60-cybercore-exec.rules" in targets
    assert "/etc/sudoers.d/cybercore-exec" not in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-install.service" in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-run.service" in targets
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup-install" in targets
    assert "/usr/local/libexec/cybercore-exec/authorization.py" in targets

    index = {action.action_id: position for position, action in enumerate(manifest)}
    assert index["remove-privilege-policy"] < index["remove-vikunja-backup-install-unit"]
    assert index["remove-vikunja-backup-install-unit"] < index["systemd-reload"]
    assert index["remove-vikunja-backup-run-unit"] < index["systemd-reload"]


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text
