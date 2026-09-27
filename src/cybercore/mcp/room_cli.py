from __future__ import annotations

import argparse
import os
from pathlib import Path

from cybercore.mcp.room_app import build_room_app_server
from cybercore.mcp.room_runtime import ALLOWED_CHATGPT_IDENTITIES, build_cyberdjs_room_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyberdjs-room-mcp",
        description="Identity-bound CyberDJs Room MCP app",
    )
    parser.add_argument(
        "--actor-id",
        choices=sorted(ALLOWED_CHATGPT_IDENTITIES),
        default=os.environ.get("CYBERDJS_ROOM_ACTOR_ID"),
    )
    parser.add_argument(
        "--room-id",
        default=os.environ.get("CYBERDJS_ROOM_ID", "cyberdjs-main"),
    )
    parser.add_argument(
        "--log-path",
        default=os.environ.get("CYBERDJS_ROOM_LOG_PATH"),
    )
    parser.add_argument(
        "--display-name",
        default=os.environ.get("CYBERDJS_ROOM_DISPLAY_NAME"),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Serve identity-bound room app over stdio")
    http = sub.add_parser("serve-http", help="Serve loopback-only Streamable HTTP")
    http.add_argument("--host", default="127.0.0.1")
    http.add_argument("--port", type=int, default=8767)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.actor_id:
        raise SystemExit("--actor-id or CYBERDJS_ROOM_ACTOR_ID is required")
    if not args.log_path:
        raise SystemExit("--log-path or CYBERDJS_ROOM_LOG_PATH is required")

    runtime = build_cyberdjs_room_runtime(
        Path(args.log_path),
        actor_id=args.actor_id,
        room_id=args.room_id,
        display_name=args.display_name,
        slack_webhook_url=os.environ.get("CYBERDJS_SLACK_WAKE_WEBHOOK_URL"),
    )
    server = build_room_app_server(
        runtime.backend,
        wake_enabled=bool(os.environ.get("CYBERDJS_SLACK_WAKE_WEBHOOK_URL")),
    )
    try:
        if args.command == "serve-http":
            if args.host not in {"127.0.0.1", "localhost", "::1"}:
                raise SystemExit("non-loopback MCP HTTP exposure requires separate approval")
            server.run(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                stateless_http=True,
                json_response=True,
            )
        else:
            server.run(transport="stdio")
    finally:
        runtime.close()
    return 0
