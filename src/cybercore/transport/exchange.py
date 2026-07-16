from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Sequence

from cybercore.runtime import RuntimePaths


class ExchangeTransport:
    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths

    def sync(self) -> None:
        agent = Path.home() / ".local/bin/cybercore-exchange-agent"
        if not agent.is_file():
            raise RuntimeError(f"Exchange agent not installed: {agent}")
        subprocess.run([str(agent)], check=True)

    def list_ready(self) -> Sequence[Path]:
        staged = self.paths.exchange_home / "staged"
        if not staged.is_dir():
            return ()
        return tuple(sorted(marker.parent for marker in staged.glob("WB-*/.ready") if marker.is_file()))
