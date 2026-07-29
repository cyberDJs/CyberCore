from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

CYBERCORE_THEME = Theme(
    {
        "cc.title": "bold bright_cyan",
        "cc.subtitle": "dim cyan",
        "cc.ok": "bold bright_green",
        "cc.warn": "bold yellow",
        "cc.error": "bold bright_red",
        "cc.key": "bold magenta",
        "cc.value": "white",
        "cc.muted": "dim white",
    }
)


@dataclass(frozen=True)
class StatusRow:
    name: str
    state: str
    detail: str


def make_console(*, no_color: bool = False) -> Console:
    return Console(theme=CYBERCORE_THEME, no_color=no_color)


def banner(console: Console, subtitle: str) -> None:
    console.print(
        Panel.fit(
            "[cc.title]CYBERCORE[/cc.title]\n"
            f"[cc.subtitle]{subtitle}[/cc.subtitle]",
            border_style="bright_cyan",
        )
    )


def status_table(rows: Iterable[StatusRow], *, title: str = "Status") -> Table:
    table = Table(title=title, header_style="cc.title")
    table.add_column("State", no_wrap=True)
    table.add_column("Component", style="cc.key")
    table.add_column("Detail")
    for row in rows:
        normalized = row.state.lower()
        style = {
            "ok": "cc.ok",
            "ready": "cc.ok",
            "warn": "cc.warn",
            "warning": "cc.warn",
            "error": "cc.error",
            "failed": "cc.error",
        }.get(normalized, "cc.value")
        table.add_row(f"[{style}]{row.state.upper()}[/{style}]", row.name, row.detail)
    return table


def step(console: Console, index: int, title: str, detail: str) -> None:
    console.print(f"\n[cc.key]{index:02d}[/cc.key] [cc.title]{title}[/cc.title]")
    console.print(f"   [cc.muted]{detail}[/cc.muted]")
