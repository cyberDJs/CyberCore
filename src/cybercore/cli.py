from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cybercore.artifact import ArtifactBuildError
from cybercore.commands.apply import run_apply
from cybercore.commands.build import run_build
from cybercore.commands.doctor import run_doctor
from cybercore.commands.plan import plan_lines, run_plan
from cybercore.commands.status import status_lines
from cybercore.commands.sync import run_sync
from cybercore.commands.validate import markdown_report, run_validate
from cybercore.commands.verify import run_verify
from cybercore.runtime import RuntimePaths
from cybercore.workblock import WorkBlockError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybercore", description="CyberCore Runtime Alpha")
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Verify local runtime dependencies")
    sub.add_parser("status", help="Show runtime and Exchange state")
    sub.add_parser("sync", help="Synchronize Exchange and list READY Work Blocks")
    sub.add_parser("plan", help="Generate prioritized actions from registry findings")
    validate_parser = sub.add_parser("validate", help="Validate registry and knowledge records")
    validate_parser.add_argument("--markdown", action="store_true", help="Render a Markdown validation report")
    verify_parser = sub.add_parser("verify", help="Verify a CXP Work Block package")
    verify_parser.add_argument("path", type=Path)
    apply_parser = sub.add_parser("apply", help="Verify and apply a CXP Work Block package")
    apply_parser.add_argument("path", type=Path)
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument("--yes", action="store_true")
    build_cmd = sub.add_parser("build", help="Build a deterministic CXP artifact")
    build_cmd.add_argument("source", type=Path)
    build_cmd.add_argument("--output", type=Path, required=True)
    build_cmd.add_argument("--artifact-id", required=True)
    build_cmd.add_argument("--version", default="1.0.0")
    build_cmd.add_argument("--publisher-id", default="cyberdjs")
    build_cmd.add_argument("--publisher-name", default="CyberDJS")
    build_cmd.add_argument("--runtime", dest="runtime_compatibility", default=">=0.1.0a1,<0.2.0")
    build_cmd.add_argument("--risk", choices=("low", "medium", "high", "critical"), default="low")
    build_cmd.add_argument("--title", required=True)
    build_cmd.add_argument("--description", default="")
    build_cmd.add_argument("--created-at")
    return parser


def _confirm(identifier: str, risk: str) -> bool:
    return input(f"Apply {identifier} (risk={risk})? Type APPLY to continue: ") == "APPLY"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    try:
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
            ready = run_sync(paths)
            if args.as_json:
                print(json.dumps({"ready": ready}, indent=2))
            else:
                print(f"READY={len(ready)}")
                for item in ready:
                    print(item)
            return 0
        if args.command == "plan":
            actions = run_plan(paths.repo)
            if args.as_json:
                print(json.dumps({"planned": [action.as_dict() for action in actions]}, indent=2))
            else:
                print("\n".join(plan_lines(actions)))
            return 0
        if args.command == "validate":
            report = run_validate(paths.repo)
            if args.as_json:
                print(json.dumps(report.as_dict(), indent=2))
            elif args.markdown:
                print(markdown_report(report))
            else:
                state = "PASS" if report.successful else "FAIL"
                print(f"{state} files={report.files_checked} records={report.records_checked} errors={len(report.errors)} warnings={len(report.warnings)}")
                for finding in report.findings:
                    print(f"{finding.severity.upper():7} {finding.code}: {finding.path}: {finding.message}")
            return 0 if report.successful else 1
        if args.command == "verify":
            report = run_verify(args.path)
            payload = {"id": report.manifest.identifier, "title": report.manifest.title, "risk": report.manifest.risk, "verified_files": len(report.verified_files)}
            print(json.dumps(payload, indent=2) if args.as_json else f"VERIFIED {payload['id']} files={payload['verified_files']} risk={payload['risk']}")
            return 0
        if args.command == "apply":
            report = run_verify(args.path)
            if not args.dry_run and not args.yes and not _confirm(report.manifest.identifier, report.manifest.risk):
                print("Apply cancelled.")
                return 0
            result = run_apply(report, paths, dry_run=args.dry_run)
            print(f"{'DRY-RUN' if result.dry_run else 'APPLIED'} {result.report.manifest.identifier}")
            return 0
        if args.command == "build":
            result = run_build(args.source, args.output, artifact_id=args.artifact_id, version=args.version, publisher_id=args.publisher_id, publisher_name=args.publisher_name, runtime_compatibility=args.runtime_compatibility, risk=args.risk, title=args.title, description=args.description, created_at=args.created_at)
            payload = {"artifact": str(result.artifact_path), "artifact_id": result.artifact_id, "digest": f"sha256:{result.artifact_digest}", "payload_digest": f"sha256:{result.payload_digest}"}
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                print(f"BUILT {result.artifact_path}")
                print(f"DIGEST sha256:{result.artifact_digest}")
            return 0
    except (ArtifactBuildError, RuntimeError, WorkBlockError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
