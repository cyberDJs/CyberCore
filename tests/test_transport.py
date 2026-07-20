from pathlib import Path

from cybercore.runtime import RuntimePaths
from cybercore.transport.exchange import ExchangeTransport


def test_list_ready(tmp_path: Path) -> None:
    exchange = tmp_path / "exchange"
    marker = exchange / "staged" / "WB-0008-demo" / ".ready"
    marker.parent.mkdir(parents=True)
    marker.touch()
    paths = RuntimePaths(
        repo=tmp_path, exchange_home=exchange, config_file=tmp_path / "exchange.env"
    )
    assert [item.name for item in ExchangeTransport(paths).list_ready()] == [
        "WB-0008-demo"
    ]
