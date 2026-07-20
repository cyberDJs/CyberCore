from __future__ import annotations

from dataclasses import dataclass

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
       