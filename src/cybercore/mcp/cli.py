from __future__ import annotations

import argparse
import json
import shutil

from cybercore.mcp.server import build_server, capability_manifest
from cybercore.runtime import RuntimePaths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybercore-mcp", description="CyberCore read-only MCP")
    parser.add_argument("--repo", help="CyberCore repository path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Serve CyberCore MCP over stdio")
    sub.add_parser("capabilities", help="Print machine-readable MCP capabilities")
    sub.add_parser("doctor", help="Check MCP prerequisites without starting the server")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capabilities":
        print(json.dumps(capability_manifest(), indent=2))
        return 0
    if args.command == "doctor":
        paths = RuntimePaths.discover(args.repo)
        checks = {
            "python_package": True,
            "repository": (paths.repo / ".cybercore" / "project.yaml").is_file(),
            "schemas": (paths.repo / "schemas" / "ccl" / "v1").is_dir(),
            "tunnel_client": shutil.which("tunnel-client") is not None,
        }
        print(json.dumps(checks, indent=2))
        return 0 if checks["python_package"] and checks["repository"] and checks["schemas"] else 1
    build_server(args.repo).run(transport="stdio")
    return 0
