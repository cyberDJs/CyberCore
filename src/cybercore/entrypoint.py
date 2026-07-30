from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cybercore import cli
from cybercore.post_merge import (
    PostMergeTransitionError,
    plan_post_merge_transition,
    render_post_merge_preview,
)
from cybercore.post_merge_state import (
    plan_post_merge_state_update,
    render_post_merge_state_preview,
)
from cybercore.runtime import RuntimePaths


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


def _state_arguments(args: argparse.Namespace) -> dict[str, object] | None:
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
        **{name: getattr(args, name) for name in scalar_names},
        "next_scope": tuple(args.next_scope),
        "next_tasks": tuple(args.next_task),
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


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "post-merge" not in arguments:
        return cli.main(arguments)
    try:
        return _run_post_merge(arguments)
    except (FileNotFoundError, PostMergeTransitionError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
