from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    repo: Path
    exchange_home: Path
    config_file: Path

    @classmethod
    def discover(cls, repo: str | None = None) -> "RuntimePaths":
        repo_path = Path(repo or os.environ.get("CYBERCORE_REPO", "") or Path.cwd()).expanduser().resolve()
        exchange_home = Path(os.environ.get("CYBERCORE_EXCHANGE_HOME", "~/.local/share/cybercore/exchange")).expanduser()
        config_file = Path(os.environ.get("CYBERCORE_EXCHANGE_CONFIG", "~/.config/cybercore/exchange.env")).expanduser()
        return cls(repo=repo_path, exchange_home=exchange_home, config_file=config_file)
