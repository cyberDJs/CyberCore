"""CyberCore command-line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from cybercore.version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="AI-first infrastructure control plane for CyberDJS.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show the installed CyberCore version.")
    subparsers.add_parser(
        "inventory",
        help="Collect infrastructure inventory. Provider support follows in TASK-002.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        print(__version__)
        return 0

    if args.command == "inventory":
        print("Inventory command scaffold is ready; provider implementation is next.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
