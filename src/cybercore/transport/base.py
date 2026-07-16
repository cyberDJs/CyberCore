from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence


class TransportAdapter(Protocol):
    def sync(self) -> None: ...
    def list_ready(self) -> Sequence[Path]: ...
