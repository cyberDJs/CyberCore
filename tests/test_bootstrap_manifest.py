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
        "system.inventory",
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

    for action_id, wrapper_safe_id, target in (
        (
            "verify-vikunja-backup-install-tombstone-absent",
            "verify-vikunja-backup-install-unit-safe",
            "/etc/systemd/system/cybercore-vikunja-backup-install.service.d/90-cybercore-rollback-tombstone.conf",
        ),
        (
            "verify-vikunja-backup-run-tombstone-absent",
            "verify-vikunja-backup-run-unit-safe",
            "/etc/systemd/system/cybercore-vikunja-backup-run.service.d/90-cybercore-rollback-tombstone.conf",
        ),
    ):
        action = by_id[action_id]
        assert action.action_type.value == "VERIFY_SYSTEMD_TOMBSTONE_ABSENT"
        assert action.destination == target
        assert index[action_id] < index["server-authorization"]
        assert index[action_id] < index["revoke-existing-privilege-policy"]
        assert index[action_id] < index[wrapper_safe_id]

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
    assert server_files["/usr/local/libexec/cybercore-exec/inventory.py"].source == (
        "src/cybercore/execution/server/inventory.py"
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
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup.service.template" in targets
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template" in targets
    assert "/usr/local/libexec/cybercore-exec/authorization.py" in targets

    index = {action.action_id: position for position, action in enumerate(manifest)}
    assert index["remove-privilege-policy"] < index["verify-privilege-policy-revoked"]
    assert index["verify-privilege-policy-revoked"] < index["remove-vikunja-backup-install-unit"]
    assert index["verify-privilege-policy-revoked"] < index["remove-vikunja-backup-run-unit"]
    assert index["remove-privilege-policy"] < index["remove-vikunja-backup-install-unit"]
    assert (
        index["remove-vikunja-backup-install-unit"] < index["systemd-reload-after-wrapper-removal"]
    )
    assert index["remove-vikunja-backup-run-unit"] < index["systemd-reload-after-wrapper-removal"]


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
    quiescent_block = text[
        text.index("def wait_until_quiescent") : text.index("def quiesce_backup_entry_paths")
    ]
    assert quiescent_block.index("unit_has_pending_job(unit)") < quiescent_block.index(
        "unit_is_active(unit)"
    )
    assert "QUIESCE_TIMEOUT_SECONDS = 90.0" in text
    assert quiesce < write_script < unmask < enable_timer


def test_rollback_publishes_effective_tombstones_before_quiescence() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    pairs = (
        (
            "verify-vikunja-backup-install-wrapper-managed-or-absent",
            "ensure-vikunja-backup-install-tombstone-parent-trusted",
            "install-vikunja-backup-install-tombstone",
            "verify-vikunja-backup-install-tombstone",
            "verify-vikunja-backup-install-tombstone-effective",
            "stop-vikunja-backup-install-wrapper",
            "/etc/systemd/system/cybercore-vikunja-backup-install.service.d",
            "/etc/systemd/system/cybercore-vikunja-backup-install.service.d/90-cybercore-rollback-tombstone.conf",
            "cybercore-vikunja-backup-install.service",
        ),
        (
            "verify-vikunja-backup-run-wrapper-managed-or-absent",
            "ensure-vikunja-backup-run-tombstone-parent-trusted",
            "install-vikunja-backup-run-tombstone",
            "verify-vikunja-backup-run-tombstone",
            "verify-vikunja-backup-run-tombstone-effective",
            "stop-vikunja-backup-run-wrapper",
            "/etc/systemd/system/cybercore-vikunja-backup-run.service.d",
            "/etc/systemd/system/cybercore-vikunja-backup-run.service.d/90-cybercore-rollback-tombstone.conf",
            "cybercore-vikunja-backup-run.service",
        ),
    )
    for (
        wrapper_verify_id,
        parent_id,
        install_id,
        verify_id,
        effective_id,
        stop_id,
        parent,
        target,
        unit,
    ) in pairs:
        assert by_id[parent_id].action_type.value == "ENSURE_SYSTEMD_TOMBSTONE_PARENT_TRUSTED"
        assert by_id[parent_id].target == parent
        assert by_id[parent_id].mode == "0755"
        assert by_id[parent_id].owner == "root"
        assert by_id[parent_id].group == "root"

        assert by_id[install_id].action_type.value == (
            "INSTALL_SYSTEMD_TOMBSTONE_DROPIN_ATOMIC_DURABLE_TRUSTED_IF_ABSENT_OR_EXACT"
        )
        assert by_id[install_id].target == target
        assert by_id[install_id].source_of_truth == (
            "deploy/cybercore-exec/rollback-wrapper-tombstone.conf"
        )
        assert by_id[install_id].mode == "0644"
        assert by_id[install_id].owner == "root"
        assert by_id[install_id].group == "root"

        assert by_id[verify_id].action_type.value == "VERIFY_SYSTEMD_TOMBSTONE_TRUSTED_EXACT"
        assert by_id[verify_id].target == target
        assert by_id[verify_id].mode == "0644"
        assert by_id[verify_id].owner == "root"
        assert by_id[verify_id].group == "root"

        assert by_id[effective_id].action_type.value == "VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE"
        assert by_id[effective_id].target == unit
        assert index["verify-privilege-policy-revoked"] < index[wrapper_verify_id]
        assert index[wrapper_verify_id] < index[parent_id]
        assert index[parent_id] < index[install_id]
        assert index[install_id] < index[verify_id]
        assert index[verify_id] < index["systemd-reload-after-tombstone-barrier"]
        assert index["systemd-reload-after-tombstone-barrier"] < index[effective_id]
        assert index[effective_id] < index[stop_id]

    action_types = {action.action_type.value for action in manifest}
    assert "MASK_SYSTEMD_UNIT_RUNTIME" not in action_types
    assert "MASK_SYSTEMD_UNIT_PERSISTENT" not in action_types

    tombstone = (DEPLOY / "rollback-wrapper-tombstone.conf").read_text()
    assert "ConditionPathExists=/dev/null/cybercore-exec-wrapper-reactivation" in tombstone
    assert "RefuseManualStart=yes" in tombstone


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


def test_rollback_keeps_tombstones_and_removes_all_managed_templates() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    for action_id, target, source in (
        (
            "remove-vikunja-backup-service-template",
            "/usr/local/libexec/cybercore-exec/vikunja-backup.service.template",
            "deploy/cybercore-exec/vikunja-backup.service",
        ),
        (
            "remove-vikunja-backup-timer-template",
            "/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template",
            "deploy/cybercore-exec/vikunja-backup.timer",
        ),
    ):
        action = by_id[action_id]
        assert action.action_type.value == "REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT"
        assert action.target == target
        assert action.source_of_truth == source
        assert index["stop-vikunja-backup-service"] < index[action_id]

    assert (
        index["remove-vikunja-backup-install-unit"] < index["systemd-reload-after-wrapper-removal"]
    )
    assert index["remove-vikunja-backup-run-unit"] < index["systemd-reload-after-wrapper-removal"]
    assert (
        index["systemd-reload-after-wrapper-removal"]
        < index["verify-vikunja-backup-install-tombstone-effective-after-removal"]
    )
    assert (
        index["systemd-reload-after-wrapper-removal"]
        < index["verify-vikunja-backup-run-tombstone-effective-after-removal"]
    )
    assert (
        by_id["verify-vikunja-backup-install-tombstone-effective-after-removal"].action_type.value
        == "VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE"
    )
    assert (
        by_id["verify-vikunja-backup-run-tombstone-effective-after-removal"].action_type.value
        == "VERIFY_SYSTEMD_TOMBSTONE_EFFECTIVE"
    )

    tombstone_targets = {
        by_id["install-vikunja-backup-install-tombstone"].target,
        by_id["install-vikunja-backup-run-tombstone"].target,
    }
    removed_targets = {
        action.target
        for action in manifest
        if action.action_type.value.startswith("REMOVE_MANAGED_FILE")
    }
    assert tombstone_targets.isdisjoint(removed_targets)


def test_bootstrap_scripts_are_declarative_only() -> None:
    for name in ("install.py", "rollback.py"):
        text = (DEPLOY / name).read_text()
        assert "subprocess.run" not in text
        assert "shell=True" not in text
        assert "bash -c" not in text
        assert "sh -c" not in text


def test_bootstrap_installs_dispatcher_dependencies_before_dispatcher() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    index = {action.action_id: position for position, action in enumerate(manifest)}

    for dependency in (
        "server-authorization",
        "server-inventory",
        "server-operations",
        "server-protocol",
    ):
        assert index[dependency] < index["server-dispatcher"]


def test_rollback_removes_inventory_after_dispatcher() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    action = by_id["remove-inventory"]
    assert action.action_type.value == "REMOVE_MANAGED_FILE_IF_EXACT_OR_ABSENT"
    assert action.target == "/usr/local/libexec/cybercore-exec/inventory.py"
    assert action.source_of_truth == "src/cybercore/execution/server/inventory.py"
    assert index["remove-dispatcher"] < index["remove-inventory"]
