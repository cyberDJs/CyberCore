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
    post_merge.add_argument(
        "--write",
        action="store_true",
        help="Write the verified canonical state transition",
    )
    return parser


def _state_arguments(args: argparse.Namespace) -> tuple[str, str, str, str, str, str] | None:
    values = (
        args.completed_artifact,
        args.verification,
        args.next_artifact,
        args.next_milestone,
        args.next_branch,
        args.next_action,
    )
    supplied = [value is not None for value in values]
    if any(supplied) and not all(supplied):
        raise ValueError(
            "State transition requires --completed-artifact, --verification, "
            "--next-artifact, --next-milestone, --next-branch and --next-action"
        )
    if args.write and not all(supplied):
        raise ValueError("--write requires all canonical state transition arguments")
    return values if all(supplied) else None  # type: ignore[return-value]


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
        (
            completed_artifact,
            verification,
            next_artifact,
            next_milestone,
            next_branch,
            next_action,
        ) = state_arguments
        state_plan = plan_post_merge_state_update(
            paths.repo,
            preview,
            completed_artifact=completed_artifact,
            verification=verification,
            next_artifact=next_artifact,
            next_milestone=next_milestone,
            next_branch=next_branch,
            next_action=next_action,
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
