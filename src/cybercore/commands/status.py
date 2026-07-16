from __future__ import annotations

from cybercore.runtime import RuntimePaths
from cybercore.transport.exchange import ExchangeTransport


def status_lines(paths: RuntimePaths) -> list[str]:
    ready = ExchangeTransport(paths).list_ready()
    failed_dir = paths.exchange_home / "failed"
    failed = sum(1 for item in failed_dir.iterdir() if item.is_dir()) if failed_dir.is_dir() else 0
    return [f"repository: {paths.repo}", f"exchange: {paths.exchange_home}", f"ready: {len(ready)}", f"failed: {failed}"]
