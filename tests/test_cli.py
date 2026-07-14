"""Smoke tests for the CyberCore CLI."""

from cybercore.cli import main
from cybercore.version import __version__


def test_version_command(capsys) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_help_without_command(capsys) -> None:
    assert main([]) == 0
    assert "CyberCore" in capsys.readouterr().out


def test_inventory_scaffold(capsys) -> None:
    assert main(["inventory"]) == 0
    assert "provider implementation" in capsys.readouterr().out.lower()
