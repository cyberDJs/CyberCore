from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess

from cybercore.events import EventRecord, RuntimeEvent, emit
from cybercore.runtime import RuntimePaths
from cybercore.trusted_operation_context import enforce_trusted_operation_context
from cybercore.workblock import VerificationReport, WorkBlockError


@dataclass(frozen=True, slots=True)
class ApplyResult:
    report: VerificationReport
    returncode: int
    dry_run: bool


def _run_optional_hook(
    report: VerificationReport,
    hook_name: str,
    paths: RuntimePaths,
    *,
    required: bool = False,
) -> int:
    hook = report.path / "actions" / f"{hook_name}.sh"
    if not hook.is_file():
        if required:
            raise WorkBlockError(f"missing required hook: {hook.name}")
        return 0

    env = os.environ.copy()
    env["CYBERCORE_REPO"] = str(paths.repo)
    env["CYBERCORE_WORKBLOCK_ID"] = report.manifest.identifier

    process = subprocess.run(
        ["bash", str(hook)],
        cwd=report.path,
        env=env,
        check=False,
    )
    return process.returncode


def run_apply(
    report: VerificationReport,
    paths: RuntimePaths,
    *,
    dry_run: bool,
) -> ApplyResult:
    expected_branch = report.manifest.target_branch or None
    enforce_trusted_operation_context(
        paths.repo,
        operation="apply",
        risk="high" if dry_run else "critical",
        expected_branch=expected_branch,
        require_clean=True,
    )

    if dry_run:
        return ApplyResult(report=report, returncode=0, dry_run=True)

    workblock_id = report.manifest.identifier
    emit(EventRecord(RuntimeEvent.APPLY_STARTED, workblock_id))

    before_code = _run_optional_hook(report, "before_apply", paths)
    if before_code != 0:
        emit(
            EventRecord(
                RuntimeEvent.APPLY_FAILED,
                workblock_id,
                f"before_apply exit={before_code}",
            )
        )
        raise RuntimeError(f"before_apply hook failed with code {before_code}")

    apply_code = _run_optional_hook(
        report,
        "apply",
        paths,
        required=True,
    )

    if apply_code != 0:
        emit(
            EventRecord(
                RuntimeEvent.APPLY_FAILED,
                workblock_id,
                f"apply exit={apply_code}",
            )
        )

        emit(EventRecord(RuntimeEvent.ROLLBACK_STARTED, workblock_id))
        rollback_code = _run_optional_hook(report, "rollback", paths)

        if rollback_code == 0:
            emit(EventRecord(RuntimeEvent.ROLLBACK_OK, workblock_id))
        else:
            emit(
                EventRecord(
                    RuntimeEvent.ROLLBACK_FAILED,
                    workblock_id,
                    f"exit={rollback_code}",
                )
            )

        raise RuntimeError(f"Work Block apply action failed with code {apply_code}")

    after_code = _run_optional_hook(report, "after_apply", paths)
    if after_code != 0:
        emit(
            EventRecord(
                RuntimeEvent.APPLY_FAILED,
                workblock_id,
                f"after_apply exit={after_code}",
            )
        )
        raise RuntimeError(f"after_apply hook failed with code {after_code}")

    emit(EventRecord(RuntimeEvent.APPLY_OK, workblock_id))
    return ApplyResult(
        report=report,
        returncode=0,
        dry_run=False,
    )
