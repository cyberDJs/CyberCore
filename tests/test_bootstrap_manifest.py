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


def test_governed_backup_run_executes_backup_inside_wrapper_cgroup() -> None:
    text = (DEPLOY / "cybercore-vikunja-backup-run.service").read_text()
    assert "ExecStart=/usr/local/sbin/vikunja-backup" in text
    assert "ExecStart=/usr/bin/systemctl start vikunja-backup.service" not in text
    assert "ReadWritePaths=/opt/backups/vikunja" in text


def test_backup_unit_templates_are_deployed_as_root_owned_sources_of_truth() -> None:
    module = load_deploy_module("install")
    manifest = module.build_install_manifest()
    by_id = {action.action_id: action for action in manifest}

    service_template = by_id["vikunja-backup-service-template"]
    assert service_template.action_type.value == "INSTALL_SERVER_FILE"
    assert service_template.source == "deploy/cybercore-exec/vikunja-backup.service"
    assert service_template.destination == (
        "/usr/local/libexec/cybercore-exec/vikunja-backup.service.template"
    )
    assert service_template.mode == "0600"
    assert service_template.owner == "root"
    assert service_template.group == "root"

    timer_template = by_id["vikunja-backup-timer-template"]
    assert timer_template.action_type.value == "INSTALL_SERVER_FILE"
    assert timer_template.source == "deploy/cybercore-exec/vikunja-backup.timer"
    assert timer_template.destination == (
        "/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template"
    )
    assert timer_template.mode == "0600"
    assert timer_template.owner == "root"
    assert timer_template.group == "root"

    assert (DEPLOY / "vikunja-backup.service").is_file()
    assert (DEPLOY / "vikunja-backup.timer").is_file()


def test_backup_installer_is_fixed_shell_free_and_private() -> None:
    text = (DEPLOY / "vikunja-backup-install").read_text()
    assert "/opt/vikunja" in text
    assert "/opt/backups/vikunja" in text
    assert "vikunja-backup.service" in text
    assert "vikunja-backup.timer" in text
    assert "RETENTION_DAYS = 14" in text
    assert "write_exact(BACKUP_SCRIPT, BACKUP_SCRIPT_TEXT, 0o700)" in text
    assert (
        'SERVICE_TEMPLATE = Path("/usr/local/libexec/cybercore-exec/vikunja-backup.service.template")'
        in text
    )
    assert (
        'TIMER_TEMPLATE = Path("/usr/local/libexec/cybercore-exec/vikunja-backup.timer.template")'
        in text
    )
    assert "SERVICE_TEMPLATE.read_text()" in text
    assert "TIMER_TEMPLATE.read_text()" in text
    service_template = (DEPLOY / "vikunja-backup.service").read_text()
    timer_template = (DEPLOY / "vikunja-backup.timer").read_text()
    assert "PartOf=cybercore-vikunja-backup-run.service" in service_template
    assert "Unit=vikunja-backup.service" in timer_template
    install_unit = (DEPLOY / "cybercore-vikunja-backup-install.service").read_text()
    assert "ReadWritePaths=/usr/local/sbin /etc/systemd/system /opt/backups/vikunja" in install_unit
    assert "-/opt/backups/vikunja" not in install_unit
    assert "shell=False" in text
    assert "shell=True" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text


def test_rollback_quiesces_optional_managed_backup_schedule_before_wrapper_teardown() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    by_id = {action.action_id: action for action in manifest}
    index = {action.action_id: position for position, action in enumerate(manifest)}

    verify_timer = by_id["verify-vikunja-backup-timer-managed-or-absent"]
    assert verify_timer.action_type.value == "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    assert verify_timer.target == "vikunja-backup.timer"
    assert verify_timer.source_of_truth == "deploy/cybercore-exec/vikunja-backup.timer"

    verify_service = by_id["verify-vikunja-backup-service-managed-or-absent"]
    assert verify_service.action_type.value == "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT_OR_ABSENT"
    assert verify_service.target == "vikunja-backup.service"
    assert verify_service.source_of_truth == "deploy/cybercore-exec/vikunja-backup.service"

    disable_timer = by_id["disable-vikunja-backup-timer"]
    assert disable_timer.action_type.value == "DISABLE_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    assert disable_timer.target == "vikunja-backup.timer"

    stop_service = by_id["stop-vikunja-backup-service"]
    assert stop_service.action_type.value == "STOP_SYSTEMD_UNIT_AND_WAIT_IF_PRESENT"
    assert stop_service.target == "vikunja-backup.service"

    assert index["verify-privilege-policy-revoked"] < index[
        "verify-vikunja-backup-timer-managed-or-absent"
    ]
    assert index["verify-privilege-policy-revoked"] < index[
        "verify-vikunja-backup-service-managed-or-absent"
    ]
    assert index["verify-vikunja-backup-timer-managed-or-absent"] < index[
        "disable-vikunja-backup-timer"
    ]
    assert index["verify-vikunja-backup-service-managed-or-absent"] < index[
        "stop-vikunja-backup-service"
    ]
    assert index["disable-vikunja-backup-timer"] < index["stop-vikunja-backup-service"]
    assert index["stop-vikunja-backup-service"] < index[
        "verify-vikunja-backup-install-wrapper-managed"
    ]
    assert index["stop-vikunja-backup-service"] < index[
        "verify-vikunja-backup-run-wrapper-managed"
    ]


def test_rollback_revokes_policy_and_static_wrappers_symmetrically() -> None:
    module = load_deploy_module("rollback")
    manifest = module.build_rollback_manifest()
    targets = {action.target for action in manifest if action.target}

    assert manifest[0].action_id == "remove-privilege-policy"
    assert manifest[1].action_id == "verify-privilege-policy-revoked"
    assert manifest[1].action_type.value == "VERIFY_PRIVILEGE_POLICY_REVOKED"
    by_id = {action.action_id: action for action in manifest}
    verify_install_wrapper = by_id["verify-vikunja-backup-install-wrapper-managed"]
    assert verify_install_wrapper.action_type.value == "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT"
    assert verify_install_wrapper.target == "cybercore-vikunja-backup-install.service"
    assert verify_install_wrapper.source_of_truth == (
        "deploy/cybercore-exec/cybercore-vikunja-backup-install.service"
    )
    verify_run_wrapper = by_id["verify-vikunja-backup-run-wrapper-managed"]
    assert verify_run_wrapper.action_type.value == "VERIFY_SYSTEMD_UNIT_MANAGED_EXACT"
    assert verify_run_wrapper.target == "cybercore-vikunja-backup-run.service"
    assert verify_run_wrapper.source_of_truth == (
        "deploy/cybercore-exec/cybercore-vikunja-backup-run.service"
    )
    stop_install_wrapper = by_id["stop-vikunja-backup-install-wrapper"]
    assert stop_install_wrapper.action_type.value == "STOP_SYSTEMD_UNIT_AND_WAIT"
    assert stop_install_wrapper.target == "cybercore-vikunja-backup-install.service"
    stop_run_wrapper = by_id["stop-vikunja-backup-run-wrapper"]
    assert stop_run_wrapper.action_type.value == "STOP_SYSTEMD_UNIT_AND_WAIT"
    assert stop_run_wrapper.target == "cybercore-vikunja-backup-run.service"
    assert "/etc/polkit-1/rules.d/60-cybercore-exec.rules" in targets
    assert "/etc/sudoers.d/cybercore-exec" not in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-install.service" in targets
    assert "/etc/systemd/system/cybercore-vikunja-backup-run.service" in targets
    assert "/usr/local/libexec/cybercore-exec/vikunja-backup-install" in targets
    assert "/usr/local/libexec/cybercore-exec/authorization.py" in targets

    index = {action.action_id: position for position, action in enumerate(manifest)}
    assert index["remove-privilege-policy"] < index["verify-privilege-policy-revoked"]
    assert (
        index["verify-privilege-policy-revoked"]
        < index["verify-vikunja-backup-install-wrapper-managed"]
    )
    assert (
        index["verify-privilege-policy-revoked"]
        < index["verify-vikunja-backup-run-wrapper-managed"]
    )
    assert (
        index["verify-vikunja-backup-install-wrapper-managed"]
        < index["stop-vikunja-backup-install-wrapper"]
    )
    assert (
        index["verify-vikunja-backup-run-wrapper-managed"]
        < index["stop-vikunja-backup-run-wrapper"]
    )
    assert (
        index["stop-vikunja-backup-install-wrapper"] < index["remove-vikunja-backup-install-unit"]
    )
    assert index["stop-vikunja-backup-run-wrapper"] < index["remove-vikunja-backup-run-unit"]
    assert max(
        index["stop-vikunja-backup-install-wrapper"],
        index["stop-vikunja-backup-run-wrapper"],
    ) < min(
        index["remove-vikunja-backup-install-unit"],
        index["remove-vikunja-backup-run-unit"],
    )
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
