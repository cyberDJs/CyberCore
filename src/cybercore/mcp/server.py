from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
import uuid

from mcp.server import MCPServer

from cybercore.ccl import CCLValidator
from cybercore.commands.doctor import run_doctor
from cybercore.commands.status import status_lines
from cybercore.operation_context_disclosure import (
    DisclosureMode,
    disclose_context_payload,
    sanitize_disclosure_text,
)
from cybercore.repository_identity_policy import (
    disclosed_repository_identity_policy_payload,
    evaluate_repository_identity_policy,
)
from cybercore.runtime import RuntimePaths
from cybercore.trusted_operation_context import collect_trusted_operation_context

SERVER_NAME = "CyberCore Private Control MCP"
SERVER_VERSION = "0.1.0"
MAX_TEXT_INPUT = 16_384
MAX_RESPONSE_BYTES = 262_144


@dataclass(frozen=True, slots=True)
class ToolError:
    code: str
    message: str
    request_id: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _bounded_text(value: str, *, name: str) -> str:
    if len(value.encode("utf-8")) > MAX_TEXT_INPUT:
        raise ValueError(f"{name} exceeds {MAX_TEXT_INPUT} bytes")
    return value


def _safe_result(payload: dict[str, object]) -> dict[str, object]:
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("MCP response exceeds configured size limit")
    return payload


def _request_id() -> str:
    return uuid.uuid4().hex


def _invoke(tool: str, fn):
    request_id = _request_id()
    started = time.monotonic()
    try:
        result = fn(request_id)
        status = "ok"
        return _safe_result(result)
    except Exception as exc:  # boundary: MCP must return deterministic sanitized errors
        status = "error"
        return {
            "ok": False,
            "error": ToolError(
                code=type(exc).__name__,
                message=sanitize_disclosure_text(exc),
                request_id=request_id,
            ).as_dict(),
        }
    finally:
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        # stderr/logging is intentionally left to the host logger; stdout is MCP protocol only.
        import logging

        logging.getLogger("cybercore.mcp.audit").info(
            "tool=%s request_id=%s status=%s duration_ms=%s",
            tool,
            request_id,
            status,
            duration_ms,
        )


def capability_manifest() -> dict[str, object]:
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": ["stdio"],
        "mode": "read_only",
        "tools": [
            "cybercore.capabilities",
            "cybercore.status",
            "cybercore.project_context",
            "cybercore.verify.repository",
            "cybercore.verify.runtime",
            "cybercore.ccl.validate",
            "cybercore.plan.change",
        ],
        "unavailable_on_canonical_main": [
            "cybercore.entities.search",
            "cybercore.entity.get",
            "cybercore.relationships.get",
            "cybercore.evidence.search",
            "cybercore.evidence.get",
            "cybercore.findings.list",
            "cybercore.finding.get",
        ],
        "mutation": {"supported": False, "approval_bypass": False},
        "limits": {"input_bytes": MAX_TEXT_INPUT, "response_bytes": MAX_RESPONSE_BYTES},
    }


def build_server(repo: str | None = None) -> MCPServer:
    paths = RuntimePaths.discover(repo)
    server = MCPServer(SERVER_NAME)

    @server.tool(name="cybercore.capabilities")
    def capabilities() -> dict[str, object]:
        """Return the explicit fail-closed CyberCore MCP capability manifest."""
        return _invoke("cybercore.capabilities", lambda rid: {"ok": True, "request_id": rid, **capability_manifest()})

    @server.tool(name="cybercore.status")
    def status() -> dict[str, object]:
        """Return sanitized local CyberCore runtime status without mutation."""
        def run(rid: str) -> dict[str, object]:
            lines = [sanitize_disclosure_text(line) for line in status_lines(paths)]
            return {"ok": True, "request_id": rid, "status": lines}
        return _invoke("cybercore.status", run)

    @server.tool(name="cybercore.project_context")
    def project_context() -> dict[str, object]:
        """Return trusted repository context through the canonical disclosure policy."""
        def run(rid: str) -> dict[str, object]:
            context = collect_trusted_operation_context(paths.repo, operation="mcp_project_context", risk="low")
            return {
                "ok": True,
                "request_id": rid,
                "context": disclose_context_payload(context.as_dict(), mode=DisclosureMode.STANDARD),
            }
        return _invoke("cybercore.project_context", run)

    @server.tool(name="cybercore.verify.repository")
    def verify_repository() -> dict[str, object]:
        """Verify repository identity against canonical CyberCore policy."""
        def run(rid: str) -> dict[str, object]:
            result = evaluate_repository_identity_policy(paths.repo)
            return {
                "ok": result.compliant,
                "request_id": rid,
                "verification": disclosed_repository_identity_policy_payload(result),
            }
        return _invoke("cybercore.verify.repository", run)

    @server.tool(name="cybercore.verify.runtime")
    def verify_runtime() -> dict[str, object]:
        """Run read-only CyberCore runtime dependency checks."""
        def run(rid: str) -> dict[str, object]:
            checks = [
                {"name": item.name, "state": str(item.state), "detail": sanitize_disclosure_text(item.detail)}
                for item in run_doctor(paths)
            ]
            return {"ok": all(item["state"].lower().endswith("ok") for item in checks), "request_id": rid, "checks": checks}
        return _invoke("cybercore.verify.runtime", run)

    @server.tool(name="cybercore.ccl.validate")
    def ccl_validate(record_json: str) -> dict[str, object]:
        """Validate one bounded CCL JSON record against canonical schemas."""
        def run(rid: str) -> dict[str, object]:
            raw = _bounded_text(record_json, name="record_json")
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("CCL record must be a JSON object")
            result = CCLValidator.from_repo(paths.repo).validate(record)
            return {"ok": result.valid, "request_id": rid, "validation": result.as_dict()}
        return _invoke("cybercore.ccl.validate", run)

    @server.tool(name="cybercore.plan.change")
    def plan_change(goal: str) -> dict[str, object]:
        """Create a non-executable change-plan envelope; never applies a change."""
        def run(rid: str) -> dict[str, object]:
            bounded = sanitize_disclosure_text(_bounded_text(goal, name="goal"))
            return {
                "ok": True,
                "request_id": rid,
                "plan": {
                    "goal": bounded,
                    "mode": "plan_only",
                    "execution_authorized": False,
                    "required_sequence": ["observe", "evidence", "reason", "plan", "explicit_approval", "apply", "verify"],
                },
            }
        return _invoke("cybercore.plan.change", run)

    return server


def serve(repo: str | None = None) -> None:
    build_server(repo).run(transport="stdio")
