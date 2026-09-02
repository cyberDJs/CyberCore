from __future__ import annotations

import argparse
import asyncio
import json
import shutil

from mcp import Client

from cybercore.mcp.server import AVAILABLE_TOOLS, build_server, capability_manifest
from cybercore.operation_context_disclosure import sanitize_disclosure_text
from cybercore.runtime import RuntimePaths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cybercore-mcp", description="CyberCore read-only MCP")
    parser.add_argument("--repo", help="CyberCore repository path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Serve CyberCore MCP over stdio")
    sub.add_parser("capabilities", help="Print machine-readable MCP capabilities")
    sub.add_parser("doctor", help="Check MCP prerequisites without starting the stdio daemon")
    return parser


async def _protocol_doctor(repo: str | None) -> dict[str, bool]:
    async with Client(build_server(repo)) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        capabilities = await client.call_tool("cybercore.capabilities", {})
        structured = capabilities.structured_content
        return {
            "mcp_protocol": True,
            "tool_registration": names == set(AVAILABLE_TOOLS),
            "capabilities_call": (
                isinstance(structured, dict)
                and structured.get("mode") == "read_only"
                and structured.get("ok") is True
            ),
        }


def _doctor_checks(repo: str | None) -> dict[str, object]:
    paths = RuntimePaths.discover(repo)
    checks: dict[str, object] = {
        "python_package": True,
        "repository": (paths.repo / ".cybercore" / "project.yaml").is_file(),
        "schemas": (paths.repo / "schemas" / "ccl" / "v1").is_dir(),
        "tunnel_client": shutil.which("tunnel-client") is not None,
    }

    disclosure_probe = sanitize_disclosure_text(
        "token=cybercore-doctor-secret /private/cybercore/path"
    )
    checks["disclosure"] = (
        "cybercore-doctor-secret" not in disclosure_probe
        and "/private/cybercore/path" not in disclosure_probe
    )

    try:
        checks.update(asyncio.run(_protocol_doctor(repo)))
    except Exception as exc:
        checks.update(
            {
                "mcp_protocol": False,
                "tool_registration": False,
                "capabilities_call": False,
                "protocol_error": sanitize_disclosure_text(exc),
            }
        )
    return checks


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capabilities":
        print(json.dumps(capability_manifest(), indent=2))
        return 0
    if args.command == "doctor":
        checks = _doctor_checks(args.repo)
        print(json.dumps(checks, indent=2))
        required = (
            "python_package",
            "repository",
            "schemas",
            "disclosure",
            "mcp_protocol",
            "tool_registration",
            "capabilities_call",
        )
        return 0 if all(checks.get(name) is True for name in required) else 1
    build_server(args.repo).run(transport="stdio")
    return 0
