from __future__ import annotations

from pathlib import Path
import subprocess

from cybercore.events import EventRecord, RuntimeEvent, emit
from cybercore.workblock import VerificationReport, verify_workblock


def run_verify(path: Path) -> VerificationReport:
    report = verify_workblock(path)
    emit(EventRecord(RuntimeEvent.VERIFY_STARTED, report.manifest.identifier))

    process = subprocess.run(
        ["bash", "actions/verify.sh"],
        cwd=report.path,
        check=False,
    )

    if process.returncode != 0:
        emit(
            EventRecord(
                RuntimeEvent.VERIFY_FAILED,
                report.manifest.identifier,
                f"exit={process.returncode}",
            )
        )
        raise RuntimeError(
            f"Work Block verify action failed with code {process.returncode}"
        )

    emit(EventRecord(RuntimeEvent.VERIFY_OK, report.manifest.identifier))
    return report
