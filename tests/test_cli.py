from pathlib import Path

from cybercore.cli import main


def test_status_command(tmp_path: Path, capsys) -> None:
    rc = main(["--repo", str(tmp_path), "status"])
    assert rc == 0
    assert "ready: 0" in capsys.readouterr().out
