from __future__ import annotations

import argparse
import json
import sys
from typing import TypedDict, cast

from cybercore import cli
from cybercore.operation_context_disclosure import (
    DisclosureMode,
    disclose_context_payload,
    render_disclosed_context,
    sanitize_disclosure_text,
)
from cybercore.post_merge import (
    PostMergeTransitionError,
    plan_post_merge_transition,
    render_post_merge_preview,
)
from cybercore.post_merge_state import (
    plan_post_merge_state_update,
    render_post_merge_state_preview,
)
from cybercore.repository_identity import (
    RepositoryIdentityError,
    disclosed_repository_identity_payload,
    render_repository_identity,
    resolve_repository_identity,
)
from cybercore.repository_identity_policy import (
    RepositoryIdentityPolicyError,
    disclosed_repository_identity_policy_payload,
    evaluate_repository_identity_policy,
    render_repository_identity_policy,
)
from cybercore.runtime import RuntimePaths
from cybercore.trusted_operation_context import (
    TrustedOperationContextError,
    collect_trusted_operation_context,
)


class _StateArguments(TypedDict):
    completed_artifact: str
    verification: str
    next_artifact: str
    next_milestone: str
    next_branch: str
    next_action: str
    completed_status: str
    next_status: str
    next_objective: str
    next_scope: tuple[str, ...]
    next_tasks: tuple[str, ...]


def _post_merge_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="CyberCore Foundation Runtime",
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)

    post_merge = sub.add_parser(
        "post-merge",
        help="Verify and apply a merged pull-request state transition",
    )
    post_merge.add_argument("pull_request", type=int)
    post_merge.add_argument("--stable-branch", default="main")
    post_merge.add_argument("--expected-head-sha")
    post_merge.add_argument("--completed-artifact")
    post_merge.add_argument("--verification")
    post_merge.add_argument("--next-artifact")
    post_merge.add_argument("--next-milestone")
    post_merge.add_argument("--next-branch")
    post_merge.add_argument("--next-action")
    post_merge.add_argument("--completed-status")
    post_merge.add_argument("--next-status")
    post_merge.add_argument("--next-objective")
    post_merge.add_argument("--next-scope", action="append", default=[])
    post_merge.add_argument("--next-task", action="append", default=[])
    post_merge.add_argument(
        "--write",
        action="store_true",
        help="Write the verified canonical state transition",
    )
    return parser


def _identity_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="CyberCore Foundation Runtime",
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    identity = sub.add_parser(
        "identity",
        help="Inspect and verify canonical repository identity",
    )
    identity.add_argument(
        "--strict",
        action="store_true",
        help="Reject deterministic path fallback when origin is unavailable or invalid",
    )
    disclosure = identity.add_mutually_exclusive_group()
    disclosure.add_argument(
        "--redact",
        action="store_true",
        help="Redact operational and sensitive identity fields",
    )
    disclosure.add_argument(
        "--full",
        action="store_true",
        help="Include sensitive identity fields; credentials remain omitted",
    )
    identity_sub = identity.add_subparsers(dest="identity_command")
    verify = identity_sub.add_parser(
        "verify",
        help="Verify resolved identity against canonical project policy",
    )
    verify.add_argument(
        "--advisory",
        action="store_true",
        help="Report policy mismatch as a warning instead of a failing exit status",
    )
    return parser


def _context_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore",
        description="CyberCore Foundation Runtime",
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    context = sub.add_parser(
        "context",
        help="Collect a trusted operation context",
    )
    context.add_argument("--operation", default="inspect")
    context.add_argument(
        "--risk",
        choices=("low", "medium", "high", "critical"),
        default="low",
    )
    context.add_argument("--expected-branch")
    context.add_argument("--expected-commit")
    context.add_argument("--require-clean", action="store_true")
    disclosure = context.add_mutually_exclusive_group()
    disclosure.add_argument(
        "--redact",
        action="store_true",
        help="Redact operational and sensitive context fields",
    )
    disclosure.add_argument(
        "--full",
        action="store_true",
        help="Include sensitive context fields; secret fields remain omitted",
    )
    return parser


def _state_arguments(args: argparse.Namespace) -> _StateArguments | None:
    scalar_names = (
        "completed_artifact",
        "verification",
        "next_artifact",
        "next_milestone",
        "next_branch",
        "next_action",
        "completed_status",
        "next_status",
        "next_objective",
    )
    scalar_values = [getattr(args, name) for name in scalar_names]
    any_state = any(value is not None for value in scalar_values) or bool(
        args.next_scope or args.next_task
    )
    complete = all(value is not None for value in scalar_values) and bool(
        args.next_scope and args.next_task
    )
    if any_state and not complete:
        raise ValueError(
            "State transition requires completed/next artifact metadata, capability "
            "statuses, next objective, at least one --next-scope and at least one --next-task"
        )
    if args.write and not complete:
        raise ValueError("--write requires a complete successor work block contract")
    if not complete:
        return None
    return {
        "completed_artifact": cast(str, args.completed_artifact),
        "verification": cast(str, args.verification),
        "next_artifact": cast(str, args.next_artifact),
        "next_milestone": cast(str, args.next_milestone),
        "next_branch": cast(str, args.next_branch),
        "next_action": cast(str, args.next_action),
        "completed_status": cast(str, args.completed_status),
        "next_status": cast(str, args.next_status),
        "next_objective": cast(str, args.next_objective),
        "next_scope": tuple(cast(list[str], args.next_scope)),
        "next_tasks": tuple(cast(list[str], args.next_task)),
    }


def _post_merge_payload(preview, *, mutation: str) -> dict[str, object]:
    pull_request = preview.pull_request
    return {
        "repository": pull_request.repository,
        "pull_request": pull_request.number,
        "title": pull_request.title,
        "base_branch": pull_request.base_branch,
        "head_branch": pull_request.head_branch,
        "head_sha": pull_request.head_sha,
        "merge_commit": pull_request.merge_commit,
        "stable_commit": preview.main_commit,
        "mutation": mutation,
    }


def _run_post_merge(argv: list[str]) -> int:
    args = _post_merge_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    state_arguments = _state_arguments(args)

    preview = plan_post_merge_transition(
        paths.repo,
        args.pull_request,
        stable_branch=args.stable_branch,
        expected_head_sha=args.expected_head_sha,
    )

    state_plan = None
    if state_arguments is not None:
        state_plan = plan_post_merge_state_update(
            paths.repo,
            preview,
            **state_arguments,
        )

    if args.write:
        assert state_plan is not None
        state_plan.write()
        mutation = "written"
    else:
        mutation = "preview" if state_plan is not None else "none"

    if args.as_json:
        print(json.dumps(_post_merge_payload(preview, mutation=mutation), indent=2))
    else:
        print(render_post_merge_preview(preview), end="")
        if state_plan is not None:
            print(render_post_merge_state_preview(state_plan), end="")
        if args.write:
            print("POST-MERGE STATE WRITTEN")
    return 0


def _run_identity(argv: list[str]) -> int:
    args = _identity_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    mode = _identity_disclosure_mode(args)

    if args.identity_command == "verify":
        result = evaluate_repository_identity_policy(
            paths.repo,
            advisory=args.advisory,
        )
        if args.as_json:
            print(
                json.dumps(
                    disclosed_repository_identity_policy_payload(
                        result,
                        disclosure_mode=mode,
                    ),
                    indent=2,
                )
            )
        else:
            print(render_repository_identity_policy(result, disclosure_mode=mode), end="")
        return 0 if result.compliant or args.advisory else 1

    diagnostic = resolve_repository_identity(paths.repo, strict=args.strict)
    if args.as_json:
        print(
            json.dumps(
                disclosed_repository_identity_payload(
                    diagnostic,
                    disclosure_mode=mode,
                ),
                indent=2,
            )
        )
    else:
        print(render_repository_identity(diagnostic, disclosure_mode=mode), end="")
    return 0


def _context_disclosure_mode(args: argparse.Namespace) -> DisclosureMode:
    if args.redact:
        return DisclosureMode.REDACTED
    if args.full:
        return DisclosureMode.FULL
    return DisclosureMode.STANDARD


def _identity_disclosure_mode(args: argparse.Namespace) -> DisclosureMode:
    if args.redact:
        return DisclosureMode.REDACTED
    if args.full:
        return DisclosureMode.FULL
    return DisclosureMode.STANDARD


def _run_context(argv: list[str]) -> int:
    args = _context_parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    context = collect_trusted_operation_context(
        paths.repo,
        operation=args.operation,
        risk=args.risk,
        expected_branch=args.expected_branch,
        expected_commit=args.expected_commit,
        require_clean=args.require_clean,
    )
    mode = _context_disclosure_mode(args)
    payload = context.as_dict()
    if args.as_json:
        print(json.dumps(disclose_context_payload(payload, mode=mode), indent=2))
    else:
        print(render_disclosed_context(payload, mode=mode), end="")
    return 0 if context.trusted else 1


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    routed_commands = {"post-merge", "identity", "context"}
    if not any(command in arguments for command in routed_commands):
        return cli.main(arguments)
    try:
        if "identity" in arguments:
            return _run_identity(arguments)
        if "context" in arguments:
            return _run_context(arguments)
        return _run_post_merge(arguments)
    except (
        FileNotFoundError,
        PostMergeTransitionError,
        RepositoryIdentityError,
        RepositoryIdentityPolicyError,
        TrustedOperationContextError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {sanitize_disclosure_text(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
