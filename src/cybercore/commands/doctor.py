from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from cybercore.knowledge import validate_repository
from cybercore.models import CheckResult, CheckState
from cybercore.registry import Registry, RegistryError
from cybercore.registry_graph import RegistryGraph
from cybercore.runtime import RuntimePaths


def _command_check(command: str) -> CheckResult:
    path = shutil.which(command)
    return CheckResult(command, CheckState.OK if path else CheckState.ERROR, path or "not found in PATH")


def _registry_checks(repo: Path) -> list[CheckResult]:
    try:
        registry = Registry.load(repo)
    except RegistryError as exc:
        return [CheckResult("registry", CheckState.ERROR, str(exc))]

    results = [CheckResult("registry", CheckState.OK, f"{len(registry)} entities loaded")]

    try:
        graph = RegistryGraph.load(registry)
    except RegistryError as exc:
        results.append(CheckResult("registry-graph", CheckState.ERROR, str(exc)))
    else:
        results.append(CheckResult("registry-graph", CheckState.OK, f"{len(graph)} relationships indexed"))

    unknowns = registry.unknowns()
    high_priority = registry.unknowns("high")
    unknown_state = CheckState.WARN if unknowns else CheckState.OK
    results.append(
        CheckResult(
            "registry-unknowns",
            unknown_state,
            f"{len(unknowns)} open ({len(high_priority)} high priority)",
        )
    )

    degraded = registry.find(status="degraded")
    degraded_state = CheckState.WARN if degraded else CheckState.OK
    detail = ", ".join(record.id for record in degraded) if degraded else "none"
    results.append(CheckResult("degraded-services", degraded_state, detail))
    return results


def _knowledge_check(repo: Path) -> CheckResult:
    report = validate_repository(repo)
    if report.errors:
        state = CheckState.ERROR
    elif report.warnings:
        state = CheckState.WARN
    else:
        state = CheckState.OK
    return CheckResult(
        "knowledge",
        state,
        (
            f"files={report.files_checked} records={report.records_checked} "
            f"errors={len(report.errors)} warnings={len(report.warnings)}"
        ),
    )


def run_doctor(paths: RuntimePaths) -> list[CheckResult]:
    results = [
        CheckResult("python", CheckState.OK if sys.version_info >= (3, 11) else CheckState.ERROR, sys.version.split()[0]),
        _command_check("git"),
        _command_check("rclone"),
        _command_check("shasum"),
    ]
    git_dir = paths.repo / ".git"
    results.append(CheckResult("repository", CheckState.OK if git_dir.is_dir() else CheckState.ERROR, str(paths.repo)))
    results.append(CheckResult("exchange-home", CheckState.OK if paths.exchange_home.is_dir() else CheckState.WARN, str(paths.exchange_home)))
    agent = Path.home() / ".local/bin/cybercore-exchange-agent"
    results.append(CheckResult("exchange-agent", CheckState.OK if agent.is_file() else CheckState.WARN, str(agent)))
    if git_dir.is_dir():
        proc = subprocess.run(["git", "-C", str(paths.repo), "status", "--porcelain"], capture_output=True, text=True, check=False)
        clean = not proc.stdout.strip()
        results.append(CheckResult("working-tree", CheckState.OK if clean else CheckState.WARN, "clean" if clean else "contains local changes"))

    results.extend(_registry_checks(paths.repo))
    results.append(_knowledge_check(paths.repo))
    return results
