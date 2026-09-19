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


def test_dispatcher_loads_as_standalone_source_artifact() -> None:
    path = ROOT / "src/cybercore/execution/server/dispatcher.py"
    spec = importlib.util.spec_from_file_location("wb0038e_dispatcher_standalone", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert callable(module.execute_request)


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

    assert index["revoke-existing-privilege-policy"] < index["verify-privilege-policy-revoked"]
    assert (
        index["verify-privilege-policy-revoked"] < index["verify-vikunja-backup-install-unit-safe"]
    )
    assert index["verify-privilege-policy-revoked"] < index["verify-vikunja-backup-run-unit-safe"]

    backup_root = by_id["backup-root-directory"]
    assert backup_root.action_type.value == "ENSURE_DIRECTORY"
    assert backup_root.destination == "/opt/backups/vikunja"
    assert backup_root.mode == "0700"
    assert backup_root.owner == "root"
    assert backup_root.group == "root"

    for action_id in ("vikunja-backup-install-unit", "vikunja-backup-run-unit"):
        action = by_id[action_id]
        assert action.action_type.value == "INSTALL_SYSTEMD_UNIT"
        assert (ROOT / action.source).is_file()
        assert action.mode == "0644"
        assert action.owner == "root"
        assert action.group == "root"
        assert index["verify-privilege-policy-revoked"] < index[action_id]
        assert index["backup-root-directory"] < index[action_id]
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
    install_unit = (DEPLOY / "cybercore-vikunja-backup-install.service").read_text()
    assert "ReadWritePaths=/usr/local/sbin /etc/systemd/system /opt/backups/vikunja" in install_unit
    assert "-/opt/backups/vikunja" not in install_unit
    assert "shell=False" in text
    assert "shell=True" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_rollback_revokes_policy_and_static_wrappers_symmetrically() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    targets = {action.target for action in manifest if action.target}

    assert manifest[0].action_id == "remove-privilege-policy"
    assert manifest[1].action_id == "verify-privilege-policy-revoked"
    assert manifest[1].action_type.value == "VERIFY_PRIVILEGE_POLICY_REVOKED"
    assert "/etc/polkit-1/rules.d/60-cybercore-exec.rules" in targets
    assert "/etc/sudoers.d/cybercore-exec" not in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-install.service" in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-run.service" in targets
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup-install" in targets
    assert "/usr/local/libexec/cybercore-exec/authorization.py" in targets

    index = {action.action_id: position for position, action in enumerate(manifest)}
    by_id = {action.action_id: action for action in manifest}
    assert index["remove-privilege-policy"] < index["verify-privilege-policy-revoked"]

    runtime_masks = (
        (
            "mask-vikunja-backup-install-unit-runtime",
            "verify-vikunja-backup-install-unit-runtime-masked",
            "cybercore-vikunja-backup-install.service",
        ),
        (
            "mask-vikunja-backup-run-unit-runtime",
            "verify-vikunja-backup-run-unit-runtime-masked",
            "cybercore-vikunja-backup-run.service",
        ),
    )
    for mask_id, verify_id, unit in runtime_masks:
        assert by_id[mask_id].action_type.value == "MASK_SYSTEMD_UNIT_RUNTIME"
        assert by_id[mask_id].target == unit
        assert by_id[verify_id].action_type.value == "VERIFY_SYSTEMD_UNIT_MASKED"
        assert by_id[verify_id].target == unit
        assert index["verify-privilege-policy-revoked"] < index[mask_id]
        assert index[mask_id] < index[verify_id]

    quiesce = (
        (
            "stop-vikunja-backup-install-unit",
            "verify-vikunja-backup-install-unit-inactive",
            "cybercore-vikunja-backup-install.service",
        ),
        (
            "stop-vikunja-backup-run-unit",
            "verify-vikunja-backup-run-unit-inactive",
            "cybercore-vikunja-backup-run.service",
        ),
        (
            "stop-vikunja-backup-timer",
            "verify-vikunja-backup-timer-inactive",
            "vikunja-backup.timer",
        ),
        (
            "stop-vikunja-backup-service",
            "verify-vikunja-backup-service-inactive",
            "vikunja-backup.service",
        ),
    )
    for stop_id, verify_id, unit in quiesce:
        assert by_id[stop_id].action_type.value == "STOP_SYSTEMD_UNIT_IF_PRESENT"
        assert by_id[stop_id].target == unit
        assert by_id[verify_id].action_type.value == "VERIFY_SYSTEMD_UNIT_INACTIVE_OR_ABSENT"
        assert by_id[verify_id].target == unit
        assert index["verify-privilege-policy-revoked"] < index[stop_id]
        assert index[stop_id] < index[verify_id]
        assert index[verify_id] < index["remove-vikunja-backup-install-unit"]
        assert index[verify_id] < index["remove-vikunja-backup-run-unit"]

    assert index["verify-vikunja-backup-timer-inactive"] < index["stop-vikunja-backup-service"]
    assert (
        index["verify-vikunja-backup-service-inactive"]
        < index["remove-vikunja-backup-install-unit"]
    )
    assert index["verify-vikunja-backup-service-inactive"] < index["remove-vikunja-backup-run-unit"]

    persistent_masks = (
        (
            "mask-vikunja-backup-install-unit-persistent",
            "verify-vikunja-backup-install-unit-persistently-masked",
            "cybercore-vikunja-backup-install.service",
        ),
        (
            "mask-vikunja-backup-run-unit-persistent",
            "verify-vikunja-backup-run-unit-persistently-masked",
            "cybercore-vikunja-backup-run.service",
        ),
    )
    for mask_id, verify_id, unit in persistent_masks:
        assert by_id[mask_id].action_type.value == "MASK_SYSTEMD_UNIT_PERSISTENT"
        assert by_id[mask_id].target == unit
        assert by_id[verify_id].action_type.value == "VERIFY_SYSTEMD_UNIT_PERSISTENTLY_MASKED"
        assert by_id[verify_id].target == unit
        assert index["remove-vikunja-backup-install-unit"] < index[mask_id]
        assert index["remove-vikunja-backup-run-unit"] < index[mask_id]
        assert index[mask_id] < index[verify_id]
        assert index[verify_id] < index["systemd-reload-after-persistent-mask"]

    assert (
        index["systemd-reload-after-persistent-mask"]
        < index["verify-vikunja-backup-install-unit-masked-after-reload"]
    )
    assert (
        index["systemd-reload-after-persistent-mask"]
        < index["verify-vikunja-backup-run-unit-masked-after-reload"]
    )
    assert (
        by_id["verify-vikunja-backup-install-unit-masked-after-reload"].action_type.value
        == "VERIFY_SYSTEMD_UNIT_MASKED"
    )
    assert (
        by_id["verify-vikunja-backup-run-unit-masked-after-reload"].action_type.value
        == "VERIFY_SYSTEMD_UNIT_MASKED"
    )

    assert "UNMASK_SYSTEMD_UNIT_RUNTIME" not in {action.action_type.value for action in manifest}
    assert "UNMASK_SYSTEMD_UNIT_PERSISTENT" not in {action.action_type.value for action in manifest}


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text
