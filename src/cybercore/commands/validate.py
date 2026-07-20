from __future__ import annotations

from pathlib import Path

from cybercore.knowledge import ValidationReport, validate_repository


def run_validate(repo: Path) -> ValidationReport:
    return validate_repository(repo)


def markdown_report(report: ValidationReport) -> str:
    state = "PASS" if report.successful else "FAIL"
    lines = [
        f"# CyberCore Knowledge Validation: {state}",
        "",
        f"- Files checked: {report.files_checked}",
        f"- Records checked: {report.records_checked}",
        f"- Errors: {len(report.errors)}",
        f"- Warnings: {len(report.warnings)}",
    ]
    if report.findings:
        lines.extend(["", "## Findings", ""])
        for finding in report.findings:
            lines.append(f"- **{finding.severity.upper()}** `{finding.code}` `{finding.path}` — {finding.message}")
    return "\n".join(lines)
