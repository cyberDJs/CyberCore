from __future__ import annotations

import time

from cybercore.presentation import StatusRow, banner, make_console, status_table, step


def run_demo(*, scenario: str = "uc-001", delay: float = 0.15, no_color: bool = False) -> int:
    if scenario != "uc-001":
        raise ValueError(f"Unknown demo scenario: {scenario}")

    console = make_console(no_color=no_color)
    banner(console, "Reality to Evidence — deterministic demonstration")

    stages = [
        ("Observe reality", "Read provider-neutral demo inventory."),
        ("Normalize evidence", "Convert observations into typed evidence records."),
        ("Build context", "Connect service, DNS, TLS, runtime, and ownership facts."),
        ("Assess risk", "Detect one expiring certificate and one stale runtime."),
        ("Prepare decision", "Generate a human-reviewable remediation plan."),
    ]
    for index, (title, detail) in enumerate(stages, start=1):
        step(console, index, title, detail)
        if delay:
            time.sleep(delay)

    console.print(
        status_table(
            [
                StatusRow("Entities", "ok", "12 normalized infrastructure entities"),
                StatusRow("Relationships", "ok", "19 evidence-backed relationships"),
                StatusRow("TLS certificate", "warn", "expires in 11 days"),
                StatusRow("PHP runtime", "warn", "version differs from desired state"),
                StatusRow("Mutation gate", "ready", "explicit human approval required"),
            ],
            title="UC-001 result",
        )
    )
    console.print("\n[cc.ok]DEMO COMPLETE[/cc.ok] No production systems were changed.")
    return 0
