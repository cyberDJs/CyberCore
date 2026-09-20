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
    assert index["remove-privilege-policy"] < index["verify-privilege-policy-revoked"]
    assert index["verify-privilege-policy-revoked"] < index["remove-vikunja-backup-install-unit"]
    assert index["verify-privilege-policy-revoked"] < index["remove-vikunja-backup-run-unit"]
    assert index["remove-privilege-policy"] < index["remove-vikunja-backup-install-unit"]
    assert index["remove-vikunja-backup-install-unit"] < index["systemd-reload"]
    assert index["remove-vikunja-backup-run-unit"] < index["systemd-reload"]


def test_governed_backup_run_owns_process_and_preserves_docker_ordering() -> None:
    text = (DEPLOY / "cybercore-vikunja-backup-run.service").read_text()
    assert "ExecStart=/usr/local/sbin/vikunja-backup" in text
    assert "ExecStart=/usr/bin/systemctl start vikunja-backup.service" not in text
    assert "Requires=docker.service" in text
    assert "After=docker.service" in text
    assert "ReadWritePaths=/opt/backups/vikunja /run/cybercore-vikunja-backup" in text
    assert "RuntimeDirectory=cybercore-vikunja-backup" in text
    assert "RuntimeDirectoryMode=0700" in text
    assert "RuntimeDirectoryPreserve=yes" in text
    assert "ReadWritePaths=/run" not in text
    generated_service = (DEPLOY / "vikunja-backup.service").read_text()
    assert "PartOf=cybercore-vikunja-backup-run.service" not in generated_service
    assert "RuntimeDirectory=cybercore-vikunja-backup" in generated_service
    assert "RuntimeDirectoryMode=0700" in generated_service
    assert "RuntimeDirectoryPreserve=yes" in generated_service


def test_backup_unit_templates_are_canonical_root_owned_inputs() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    by_id = {action.action_id: action for action in manifest}

    service_template = by_id["vikunja-backup-service-template"]
    assert service_template.source == "deploy/cybercore-exec/vikunja-backup.service"
    assert service_template.destination == (
        "/usr/local/libexec/cybercore-exec/vikunja-backup.service.template"
    )
    assert service_template.mode == "0600"
    assert service_template.owner == "root"
    assert service_template.group == "root"

    timer_template = by_id["vikunja-backup-timer-template"]
    assert timer_template.source == "deploy/cybercore-exec/vikunja-backup.timer"
    assert timer_template.destination == (
        "/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template"
    )
    assert timer_template.mode == "0600"
    assert timer_template.owner == "root"
    assert timer_template.group == "root"

    installer = (DEPLOY / "vikunja-backup-install").read_text()
    assert "SERVICE_TEMPLATE.read_text()" in installer
    assert "TIMER_TEMPLATE.read_text()" in installer
    assert 'LOCK_PATH = Path("/run/cybercore-vikunja-backup/backup.lock")' in installer
    assert 'LOCK_PATH = Path("/run/cybercore-vikunja-backup.lock")' not in installer
    assert "fcntl.flock(handle.fileno(), fcntl.LOCK_EX)" in installer
    assert "os.O_NOFOLLOW" in installer
    assert "os.fchmod(fd, 0o600)" in installer


def test_backup_installer_quiesces_entry_paths_before_replacing_script() -> None:
    text = (DEPLOY / "vikunja-backup-install").read_text()

    quiesce = text.index("quiesce_backup_entry_paths()")
    write_script = text.index("write_exact(BACKUP_SCRIPT, BACKUP_SCRIPT_TEXT, 0o700)")
    unmask = text.index('require_systemctl("unmask", "--runtime", MANUAL_RUN_UNIT)')
    enable_timer = text.index('require_systemctl("enable", "--now", BACKUP_TIMER_UNIT)')

    assert 'require_systemctl("mask", "--runtime", MANUAL_RUN_UNIT)' in text
    assert 'require_systemctl("stop", BACKUP_TIMER_UNIT)' in text
    assert "wait_until_quiescent(MANUAL_RUN_UNIT, deadline)" in text
    assert "wait_until_quiescent(BACKUP_TIMER_UNIT, deadline)" in text
    assert "wait_until_quiescent(BACKUP_SERVICE_UNIT, deadline)" in text
    assert 'systemctl("list-jobs", "--no-legend", "--plain", unit)' in text
    assert "return bool(completed.stdout.strip())" in text
    assert "QUIESCE_TIMEOUT_SECONDS = 90.0" in text
    assert quiesce < write_script < unmask < enable_timer


def test_rollback_blocks_new_wrapper_starts_before_quiescence() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    assert by_id["runtime-mask-vikunja-backup-install-wrapper"].action_type.value == (
        "MASK_SYSTEMD_UNIT_RUNTIME"
    )
    assert by_id["runtime-mask-vikunja-backup-run-wrapper"].action_type.value == (
        "MASK_SYSTEMD_UNIT_RUNTIME"
    )
    assert by_id["verify-vikunja-backup-install-wrapper-runtime-masked"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME"
    )
    assert by_id["verify-vikunja-backup-run-wrapper-runtime-masked"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MASKED_RUNTIME"
    )

    assert (
        index["verify-privilege-policy-revoked"]
        < index["verify-vikunja-backup-install-wrapper-managed"]
    )
    assert (
        index["verify-vikunja-backup-install-wrapper-managed"]
        < index["runtime-mask-vikunja-backup-install-wrapper"]
    )
    assert (
        index["runtime-mask-vikunja-backup-install-wrapper"]
        < index["verify-vikunja-backup-install-wrapper-runtime-masked"]
    )
    assert (
        index["verify-vikunja-backup-install-wrapper-runtime-masked"]
        < index["stop-vikunja-backup-install-wrapper"]
    )
    assert (
        index["runtime-mask-vikunja-backup-run-wrapper"]
        < index["verify-vikunja-backup-run-wrapper-runtime-masked"]
    )
    assert (
        index["verify-vikunja-backup-run-wrapper-runtime-masked"]
        < index["stop-vikunja-backup-run-wrapper"]
    )


def test_rollback_stops_installer_before_rechecking_schedule_and_service() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    assert by_id["verify-vikunja-backup-timer-managed-or-absent"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    )
    assert by_id["verify-vikunja-backup-service-managed-or-absent"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    )
    assert by_id["disable-vikunja-backup-timer"].action_type.value == (
        "DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    )
    assert by_id["stop-vikunja-backup-service"].action_type.value == (
        "STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    )

    assert (
        index["stop-vikunja-backup-install-wrapper"]
        < index["verify-vikunja-backup-timer-managed-or-absent"]
    )
    assert (
        index["stop-vikunja-backup-install-wrapper"]
        < index["verify-vikunja-backup-service-managed-or-absent"]
    )
    assert (
        index["verify-vikunja-backup-service-managed-or-absent"]
        < index["stop-vikunja-backup-run-wrapper"]
    )
    assert (
        index["verify-vikunja-backup-timer-managed-or-absent"]
        < index["disable-vikunja-backup-timer"]
    )
    assert index["disable-vikunja-backup-timer"] < index["stop-vikunja-backup-run-wrapper"]
    assert (
        index["verify-vikunja-backup-service-managed-or-absent"]
        < index["stop-vikunja-backup-service"]
    )
    assert index["disable-vikunja-backup-timer"] < index["stop-vikunja-backup-service"]
    assert index["stop-vikunja-backup-service"] < index["remove-vikunja-backup-install-unit"]
    assert index["stop-vikunja-backup-service"] < index["remove-vikunja-backup-run-unit"]


def test_rollback_persistently_masks_wrapper_names_before_reboot_boundary() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    assert by_id["persistent-mask-vikunja-backup-install-wrapper"].action_type.value == (
        "MASK_SYSTEMD_UNIT_PERSISTENT"
    )
    assert by_id["persistent-mask-vikunja-backup-run-wrapper"].action_type.value == (
        "MASK_SYSTEMD_UNIT_PERSISTENT"
    )
    assert by_id["verify-vikunja-backup-install-wrapper-persistent-masked"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT"
    )
    assert by_id["verify-vikunja-backup-run-wrapper-persistent-masked"].action_type.value == (
        "VERIFY_SYSTEMD_UNIT_MASKED_PERSISTENT"
    )

    assert (
        index["remove-vikunja-backup-install-unit"]
        < index["persistent-mask-vikunja-backup-install-wrapper"]
    )
    assert (
        index["remove-vikunja-backup-run-unit"]
        < index["persistent-mask-vikunja-backup-run-wrapper"]
    )
    assert (
        index["persistent-mask-vikunja-backup-install-wrapper"]
        < index["systemd-reload-after-persistent-mask"]
    )
    assert (
        index["persistent-mask-vikunja-backup-run-wrapper"]
        < index["systemd-reload-after-persistent-mask"]
    )
    assert (
        index["systemd-reload-after-persistent-mask"]
        < index["verify-vikunja-backup-install-wrapper-persistent-masked"]
    )
    assert (
        index["systemd-reload-after-persistent-mask"]
        < index["verify-vikunja-backup-run-wrapper-persistent-masked"]
    )


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text
