from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from cybercore.models import CheckResult, CheckState
from cybercore.runtime import RuntimePaths


def _command_check(command: str) -> CheckResult:
    path = shutil.which(command)
    return CheckResult(command, CheckState.OK if path else CheckState.ERROR, path or "not found in PATH")


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
    return results
