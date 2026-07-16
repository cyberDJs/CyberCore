from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cybercore.commands.apply import run_apply
from cybercore.commands.doctor import run_doctor
from cybercore.commands.status import status_lines
from cybercore.commands.sync import run_sync
from cybercore.commands.verify import run_verify
from cybercore.runtime import RuntimePaths
from cybercore.workblock import WorkBlockError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="CyberCore Runtime Alpha",
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Verify local runtime dependencies")
    sub.add_parser("status", help="Show runtime and Exchange state")
    sub.add_parser("sync", help="Synchronize Exchange and list READY Work Blocks")

    verify_parser = sub.add_parser(
        "verify",
        help="Verify a CXP Work Block package",
    )
    verify_parser.add_argument("path", type=Path)

    apply_parser = sub.add_parser(
        "apply",
        help="Verify and apply a CXP Work Block package",
    )
    apply_parser.add_argument("path", type=Path)
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify safety gates without executing actions/apply.sh",
    )
    apply_parser.add_argument(
        "--yes",
        action="store_true",
        help="Approve execution without interactive confirmation",
    )
    return parser


def _confirm(identifier: str, risk: str) -> bool:
    answer = input(
        f"Apply {identifier} (risk={risk})? Type APPLY to continue: "
    )
    return answer == "APPLY"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)

    try:
        if args.command == "doctor":
            results = run_doctor(paths)
            if args.as_json:
                print(json.dumps([
                    {"name": r.name, "state": r.state, "detail": r.detail}
                    for r in results
                ], indent=2))
            else:
                for result in results:
                    print(
                        f"{result.state.upper():5} "
                        f"{result.name}: {result.detail}"
                    )
            return 0 if all(r.successful for r in results) else 1

        if args.command == "status":
            lines = status_lines(paths)
            print(
                json.dumps(lines, indent=2)
                if args.as_json
                else "\n".join(lines)
            )
            return 0

        if args.command == "sync":
            ready = run_sync(paths)
            if args.as_json:
                print(json.dumps({"ready": ready}, indent=2))
            else:
                print(f"READY={len(ready)}")
                for item in ready:
                    print(item)
            return 0

        if args.command == "verify":
            report = run_verify(args.path)
            payload = {
                "id": report.manifest.identifier,
                "title": report.manifest.title,
                "risk": report.manifest.risk,
                "verified_files": len(report.verified_files),
            }
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                print(
                    f"VERIFIED {payload['id']} "
                    f"files={payload['verified_files']} "
                    f"risk={payload['risk']}"
                )
            return 0

        if args.command == "apply":
            report = run_verify(args.path)

            if not args.dry_run and not args.yes:
                if not _confirm(
                    report.manifest.identifier,
                    report.manifest.risk,
                ):
                    print("Apply cancelled.")
                    return 0

            result = run_apply(
                report,
                paths,
                dry_run=args.dry_run,
            )
            action = "DRY-RUN" if result.dry_run else "APPLIED"
            print(f"{action} {result.report.manifest.identifier}")
            return 0

    except (RuntimeError, WorkBlockError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
