from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cybercore.artifact import ArtifactBuildError
from cybercore.ccl import CCLValidationError, CCLValidator
from cybercore.checkpoint import CheckpointError, collect_checkpoint, render_checkpoint
from cybercore.checkpoint_evidence import resolve_test_result
from cybercore.checkpoint_memory import plan_memory_update, render_memory_preview
from cybercore.commands.apply import run_apply
from cybercore.commands.build import run_build
from cybercore.commands.doctor import run_doctor
from cybercore.commands.status import status_lines
from cybercore.commands.sync import run_sync
from cybercore.commands.verify import run_verify
from cybercore.demo import run_demo
from cybercore.learn import run_lesson
from cybercore.runtime import RuntimePaths
from cybercore.workblock import WorkBlockError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore", description="CyberCore Foundation Runtime"
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Verify local runtime dependencies")
    sub.add_parser("status", help="Show runtime and Exchange state")
    sub.add_parser("sync", help="Synchronize Exchange and list READY Work Blocks")

    checkpoint_parser = sub.add_parser(
        "checkpoint", help="Collect a repository checkpoint"
    )
    checkpoint_parser.add_argument(
        "--output",
        type=Path,
        help="Write rendered checkpoint to this file instead of stdout",
    )
    checkpoint_parser.add_argument(
        "--memory",
        action="store_true",
        help="Preview canonical PROJECT_STATE.md and WORKLOG.md updates",
    )
    checkpoint_parser.add_argument(
        "--write",
        action="store_true",
        help="Write canonical memory updates; requires --memory",
    )
    checkpoint_parser.add_argument(
        "--test-result",
        help="Manual verified test evidence, for example '18 passed in 3.23s'",
    )
    checkpoint_parser.add_argument(
        "--evidence",
        type=Path,
        help="Structured verification evidence JSON; requires --memory",
    )
    checkpoint_parser.add_argument(
        "--next-action",
        help="Next planned action to append to WORKLOG.md",
    )

    verify_parser = sub.add_parser("verify", help="Verify a CXP Work Block package")
    verify_parser.add_argument("path", type=Path)

    apply_parser = sub.add_parser(
        "apply", help="Verify and apply a CXP Work Block package"
    )
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
    build_cmd.add_argument(
        "--runtime", dest="runtime_compatibility", default=">=0.1.0,<0.2.0"
    )
    build_cmd.add_argument(
        "--risk", choices=("low", "medium", "high", "critical"), default="low"
    )
    build_cmd.add_argument("--title", required=True)
    build_cmd.add_argument("--description", default="")
    build_cmd.add_argument("--created-at")

    demo_parser = sub.add_parser(
        "demo", help="Run a deterministic, read-only CyberCore demonstration"
    )
    demo_parser.add_argument("--scenario", default="uc-001", choices=("uc-001",))
    demo_parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Delay between presentation steps in seconds",
    )
    demo_parser.add_argument("--no-color", action="store_true")

    learn_parser = sub.add_parser(
        "learn", help="Run an interactive CyberCore learning lesson"
    )
    learn_parser.add_argument("--lesson", default="evidence", choices=("evidence",))
    learn_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run the lesson without waiting for keyboard input",
    )
    learn_parser.add_argument("--no-color", action="store_true")

    ccl_parser = sub.add_parser("ccl", help="Work with CyberCore Canonical Language")
    ccl_sub = ccl_parser.add_subparsers(dest="ccl_command", required=True)
    ccl_validate = ccl_sub.add_parser("validate", help="Validate a canonical record")
    ccl_validate.add_argument("path", type=Path)

    return parser


def _confirm(identifier: str, risk: str) -> bool:
    return (
        input(f"Apply {identifier} (risk={risk})? Type APPLY to continue: ") == "APPLY"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "demo":
            if args.delay < 0:
                raise ValueError("Demo delay must be zero or greater")
            return run_demo(
                scenario=args.scenario,
                delay=args.delay,
                no_color=args.no_color,
            )

        if args.command == "learn":
            return run_lesson(
                lesson=args.lesson,
                interactive=not args.non_interactive,
                no_color=args.no_color,
            )

        if args.command == "ccl":
            repo = Path(args.repo or ".").resolve()
            validator = CCLValidator.from_repo(repo)
            result = validator.validate_file(args.path)
            payload = result.as_dict()
            if args.as_json:
                print(json.dumps(payload, indent=2))
            elif result.valid:
                print(f"VALID {result.record_id} schema={result.schema_id}")
            else:
                print(f"INVALID {result.record_id} schema={result.schema_id}")
                for issue in result.errors:
                    print(f"ERROR {issue.code} {issue.path}: {issue.message}")
            return 0 if result.valid else 1

        paths = RuntimePaths.discover(args.repo)

        if args.command == "checkpoint":
            if args.write and not args.memory:
                raise ValueError("--write requires --memory")
            if args.memory and args.output:
                raise ValueError("--output cannot be combined with --memory")
            if args.evidence and not args.memory:
                raise ValueError("--evidence requires --memory")

            checkpoint = collect_checkpoint(paths.repo)
            evidence_path = args.evidence
            if evidence_path is not None:
                evidence_path = evidence_path.expanduser()
                if not evidence_path.is_absolute():
                    evidence_path = paths.repo / evidence_path
            test_result, _evidence = resolve_test_result(
                checkpoint,
                evidence_path=evidence_path,
                test_result=args.test_result,
            )

            if args.memory:
                plan = plan_memory_update(
                    paths.repo,
                    checkpoint,
                    test_result=test_result,
                    next_action=args.next_action,
                )
                if args.write:
                    plan.write()
                    print("CHECKPOINT MEMORY WRITTEN")
                else:
                    print(render_memory_preview(plan), end="")
                return 0

            if args.as_json:
                rendered = json.dumps(checkpoint.as_dict(), indent=2)
            else:
                rendered = render_checkpoint(checkpoint)
            if args.output:
                output = args.output.expanduser()
                if not output.is_absolute():
                    output = paths.repo / output
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered + ("\n" if args.as_json else ""), encoding="utf-8")
                print(f"CHECKPOINT {output}")
            else:
                print(rendered, end="" if rendered.endswith("\n") else "\n")
            return 0

        if args.command == "doctor":
            results = run_doctor(paths)
            if args.as_json:
                print(
                    json.dumps(
                        [
                            {"name": r.name, "state": r.state, "detail": r.detail}
                            for r in results
                        ],
                        indent=2,
                    )
                )
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

        if args.command == "verify":
            report = run_verify(args.path)
            payload = {
                "id": report.manifest.identifier,
                "title": report.manifest.title,
                "risk": report.manifest.risk,
                "verified_files": len(report.verified_files),
            }
            print(
                json.dumps(payload, indent=2)
                if args.as_json
                else f"VERIFIED {payload['id']} files={payload['verified_files']} risk={payload['risk']}"
            )
            return 0

        if args.command == "apply":
            report = run_verify(args.path)
            if (
                not args.dry_run
                and not args.yes
                and not _confirm(report.manifest.identifier, report.manifest.risk)
            ):
                print("Apply cancelled.")
                return 0
            result = run_apply(report, paths, dry_run=args.dry_run)
            print(
                f"{'DRY-RUN' if result.dry_run else 'APPLIED'} {result.report.manifest.identifier}"
            )
            return 0

        if args.command == "build":
            result = run_build(
                args.source,
                args.output,
                artifact_id=args.artifact_id,
                version=args.version,
                publisher_id=args.publisher_id,
                publisher_name=args.publisher_name,
                runtime_compatibility=args.runtime_compatibility,
                risk=args.risk,
                title=args.title,
                description=args.description,
                created_at=args.created_at,
            )
            payload = {
                "artifact": str(result.artifact_path),
                "artifact_id": result.artifact_id,
                "digest": f"sha256:{result.artifact_digest}",
                "payload_digest": f"sha256:{result.payload_digest}",
            }
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                print(f"BUILT {result.artifact_path}")
                print(f"DIGEST sha256:{result.artifact_digest}")
            return 0
    except (
        ArtifactBuildError,
        CCLValidationError,
        CheckpointError,
        FileNotFoundError,
        RuntimeError,
        ValueError,
        WorkBlockError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())