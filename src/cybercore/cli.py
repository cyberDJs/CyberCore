from __future__ import annotations

import argparse
import json
import sys

from cybercore.commands.doctor import run_doctor
from cybercore.commands.status import status_lines
from cybercore.commands.sync import run_sync
from cybercore.runtime import RuntimePaths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybercore", description="CyberCore Runtime Alpha")
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    sub.add_parser("sync")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    if args.command == "doctor":
        results = run_doctor(paths)
        if args.as_json:
            print(json.dumps([{"name": r.name, "state": r.state, "detail": r.detail} for r in results], indent=2))
        else:
            for result in results:
                print(f"{result.state.upper():5} {result.name}: {result.detail}")
        return 0 if all(r.successful for r in results) else 1
    if args.command == "status":
        lines = status_lines(paths)
        print(json.dumps(lines, indent=2) if args.as_json else "\n".join(lines))
        return 0
    if args.command == "sync":
        try:
            ready = run_sync(paths)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        if args.as_json:
            print(json.dumps({"ready": ready}, indent=2))
        else:
            print(f"READY={len(ready)}")
            for item in ready:
                print(item)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
