from __future__ import annotations

import argparse
import os
from pathlib import Path

from cybercore.mcp.room_app import build_room_app_server
from cybercore.mcp.room_broker_client import BrokerRoomBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyberdjs-room-mcp",
        description="Identity-bound CyberDJs Room MCP frontend",
    )
    parser.add_argument(
        "--socket-path",
        default=os.environ.get("CYBERDJS_ROOM_BROKER_SOCKET"),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Serve identity-bound room app over stdio")
    http = sub.add_parser("serve-http", help="Serve loopback-only Streamable HTTP")
    http.add_argument("--host", default="127.0.0.1")
    http.add_argument("--port", type=int, default=8767)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.socket_path:
        raise SystemExit("--socket-path or CYBERDJS_ROOM_BROKER_SOCKET is required")

    communication = BrokerRoomBackend(Path(args.socket_path))
    runtime_status = communication.get_runtime_status()
    server = build_room_app_server(
        communication,
        wake_enabled=bool(runtime_status.get("wake_enabled")),
    )
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
    return 0
