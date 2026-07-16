from __future__ import annotations

from cybercore.runtime import RuntimePaths
from cybercore.transport.exchange import ExchangeTransport


def run_sync(paths: RuntimePaths) -> list[str]:
    transport = ExchangeTransport(paths)
    transport.sync()
    return [path.name for path in transport.list_ready()]
