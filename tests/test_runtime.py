from pathlib import Path

from cybercore.runtime import RuntimePaths


def test_runtime_paths_discover(tmp_path: Path) -> None:
    assert RuntimePaths.discover(str(tmp_path)).repo == tmp_path.resolve()
