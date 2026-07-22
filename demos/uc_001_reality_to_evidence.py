from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "cc.title": "bold bright_cyan",
        "cc.muted": "dim white",
        "cc.ok": "bold bright_green",
        "cc.warn": "bold yellow",
        "cc.risk": "bold bright_magenta",
        "cc.evidence": "cyan",
        "cc.decision": "bold bright_blue",
    }
)


@dataclass(frozen=True)
class DemoStep:
    label: str
    detail: str
    state: str = "ok"


def pause(seconds: float, *, instant: bool) -> None:
    if not instant:
        time.sleep(seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberCore UC-001 demo")
    parser.add_argument(
        "--instant",
        action="store_true",
        default=os.getenv("CYBERCORE_DEMO_INSTANT") == "1",
        help="Disable animation delays for tests and CI",
    )
    return parser


def run_demo(*, instant: bool = False) -> int:
    console = Console(theme=THEME)
    console.clear()
    console.print(
        Panel.fit(
            "[cc.title]CYBERCORE[/cc.title]\n"
            "[cc.muted]UC-001 · Reality → Evidence → Decision Candidate[/cc.muted]",
            border_style="bright_cyan",
            padding=(1, 4),
        )
    )

    console.print("\n[cc.muted]Target[/cc.muted]  mail.eimyherrer.com")
    console.print("[cc.muted]Mode[/cc.muted]    observation only · no mutation\n")

    with Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task("Observing operational reality…", total=None)
        pause(0.9, instant=instant)
        progress.update(task, description="Collecting DNS evidence…")
        pause(0.7, instant=instant)
        progress.update(task, description="Inspecting TLS and SMTP posture…")
        pause(0.8, instant=instant)
        progress.update(task, description="Building evidence-backed knowledge…")
        pause(0.7, instant=instant)

    steps = [
        DemoStep("DNS", "MX records resolve to the expected mail service"),
        DemoStep("TLS", "Certificate chain is valid and currently trusted"),
        DemoStep("SMTP", "Service banner and transport posture observed"),
        DemoStep("DMARC", "Policy is present but enforcement remains weak", "warn"),
    ]

    table = Table(title="Observed evidence", border_style="bright_cyan")
    table.add_column("State", width=8)
    table.add_column("Source", style="cc.evidence", width=12)
    table.add_column("Observation")
    for step in steps:
        state = "[cc.ok]PASS[/cc.ok]" if step.state == "ok" else "[cc.warn]WARN[/cc.warn]"
        table.add_row(state, step.label, step.detail)
    console.print(table)

    knowledge = Table(show_header=False, box=None, padding=(0, 1))
    knowledge.add_column(style="cc.muted", width=18)
    knowledge.add_column()
    knowledge.add_row("Entity", "mail.eimyherrer.com")
    knowledge.add_row("Entity type", "mail-service")
    knowledge.add_row("Confidence", "94%")
    knowledge.add_row("Mutation", "none")
    console.print(Panel(knowledge, title="Knowledge", border_style="blue"))

    decision = Text()
    decision.append("Candidate: ", style="cc.muted")
    decision.append("Harden DMARC from p=none to p=quarantine\n", style="cc.decision")
    decision.append("Risk: MEDIUM   Reversible: YES   Approval: REQUIRED", style="cc.risk")
    console.print(Panel(decision, title="Decision candidate", border_style="bright_magenta"))

    console.print(
        "\n[cc.ok]✓ Scenario complete[/cc.ok]  "
        "[cc.muted]Reality was observed, evidence preserved, no change applied.[/cc.muted]"
    )
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return run_demo(instant=args.instant)


if __name__ == "__main__":
    raise SystemExit(main())
