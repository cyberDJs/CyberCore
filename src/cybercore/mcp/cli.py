from __future__ import annotations

import argparse
import json

from cybercore.mcp.server import build_server, capability_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cybercore-mcp", description="CyberCore governed MCP"
    )
    parser.add_argument("--repo", help="CyberCore repository path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Serve MCP over stdio")
    http = sub.add_parser(
        "serve-http", help="Serve local-only Streamable HTTP MCP"
    )
    http.add_argument("--host", default="127.0.0.1")
    http.add_argument("--port", type=int, default=8766)
    sub.add_parser(
        "capabilities", help="Print machine-readable MCP capabilities"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capabilities":
        print(json.dumps(capability_manifest(), indent=2))
        return 0
    server = build_server(args.repo)
    if args.command == "serve-http":
        if args.host not in {"127.0.0.1", "localhost", "::1"}:
            raise SystemExit(
                "non-loopback MCP HTTP exposure requires a separate reviewed deployment"
            )
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            stateless_http=True,
            json_response=True,
        )
        return 0
    server.run(transport="stdio")
    return 0
