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
        "cc.title": "bold bright_cyan