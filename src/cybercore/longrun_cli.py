from __future__ import annotations

import argparse
import json
from pathlib import Path

from cybercore.longrun.operator import (
    event_payload,
    inspect_events,
    inspect_longrun,
    load_operator_context,
    resume_longrun,
    start_longrun,
    state_payload,
)
from cybercore.runtime import RuntimePaths


def _add_contract_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("configs/longrun/marathon16.yaml"),
        help="LongRun profile YAML, relative to --repo by default",
    )
    parser.add_argument(
        "--mission",
        type=Path,
        required=True,
        help="Concrete LongRun mission YAML, relative to --repo by default",
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        help="Override the default .cybercore/longrun/<run_id>.sqlite state database",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybercore", description="CyberCore LongRun Operator")
    parser.add_argument("--repo", help="CyberCore repository path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    longrun = sub.add_parser("longrun", help="Operate durable LongRun missions")
    commands = longrun.add_subparsers(dest="longrun_command", required=True)

    start = commands.add_parser("start", help="Create a run and execute deterministic local steps")
    _add_contract_arguments(start)
    start.add_argument("--max-steps", type=int, default=1)

    resume = commands.add_parser("resume", help="Resume an existing deterministic local run")
    _add_contract_arguments(resume)
    resume.add_argument("--max-steps", type=int, default=1)

    status = commands.add_parser("status", help="Inspect durable LongRun state")
    _add_contract_arguments(status)

    events = commands.add_parser("events", help="Inspect the append-only LongRun event ledger")
    _add_contract_arguments(events)
    events.add_argument("--limit", type=int, default=100)
    return parser


def _render_state(payload: dict[str, object]) -> str:
    return (
        f"LONGRUN {payload['run_id']} status={payload['status']} "
        f"step={payload['step_index']} score={payload['evaluator_score']}"
    )


def run_longrun(argv: list[str]) -> int:
    args = _parser().parse_args(argv)
    paths = RuntimePaths.discover(args.repo)
    context = load_operator_context(
        paths.repo,
        profile=args.profile,
        mission=args.mission,
        state_db=args.state_db,
    )

    if args.longrun_command == "start":
        state = start_longrun(context, max_steps=args.max_steps)
        payload = state_payload(state)
        print(json.dumps(payload, indent=2) if args.as_json else _render_state(payload))
        return 0

    if args.longrun_command == "resume":
        state = resume_longrun(context, max_steps=args.max_steps)
        payload = state_payload(state)
        print(json.dumps(payload, indent=2) if args.as_json else _render_state(payload))
        return 0

    if args.longrun_command == "status":
        payload = state_payload(inspect_longrun(context))
        print(json.dumps(payload, indent=2) if args.as_json else _render_state(payload))
        return 0

    events = [event_payload(event) for event in inspect_events(context, limit=args.limit)]
    if args.as_json:
        print(json.dumps(events, indent=2))
    else:
        for event in events:
            print(
                f"EVENT {event['id']} step={event['step_index']} kind={event['kind']} "
                f"payload={json.dumps(event['payload'], sort_keys=True)}"
            )
    return 0
