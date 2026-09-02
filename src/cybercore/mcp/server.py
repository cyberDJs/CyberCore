from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import time
import uuid

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

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
TOOL_TIMEOUT_SECONDS = 10.0
AVAILABLE_TOOLS = (
    "cybercore.capabilities",
    "cybercore.status",
    "cybercore.project_context",
    "cybercore.verify.repository",
    "cybercore.verify.runtime",
    "cybercore.ccl.validate",
    "cybercore.plan.change",
)
UNAVAILABLE_WORLD_MODEL_TOOLS = (
    "cybercore.entities.search",
    "cybercore.entity.get",
    "cybercore.relationships.get",
    "cybercore.evidence.search",
    "cybercore.evidence.get",
    "cybercore.findings.list",
    "cybercore.finding.get",
)
READ_ONLY_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)

_SECRET_OUTPUT_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "password",
        "passwd",
        "secret",
        "credential",
        "credentials",
        "api_key",
        "access_key",
        "private_key",
    }
)
_SECRET_OUTPUT_SUFFIXES = (
    "_token",
    "_password",
    "_secret",
    "_credential",
    "_credentials",
    "_api_key",
    "_access_key",
    "_private_key",
)
ToolCallback = Callable[[str], dict[str, object]]


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


def _is_secret_output_key(key: object) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    return normalized in _SECRET_OUTPUT_KEYS or normalized.endswith(_SECRET_OUTPUT_SUFFIXES)


def _sanitize_output(value: object) -> object:
    if isinstance(value, str):
        return sanitize_disclosure_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            name = str(key)
            sanitized[name] = "[REDACTED]" if _is_secret_output_key(name) else _sanitize_output(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_output(item) for item in value]
    return sanitize_disclosure_text(value)


def _safe_result(payload: dict[str, object]) -> dict[str, object]:
    sanitized = _sanitize_output(payload)
    if not isinstance(sanitized, dict):
        raise TypeError("MCP result must be a JSON object")
    encoded = json.dumps(sanitized, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("MCP response exceeds configured size limit")
    return sanitized


def _request_id() -> str:
    return uuid.uuid4().hex


def _error_code(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, json.JSONDecodeError):
        return "invalid_json"
    if isinstance(exc, ValueError):
        return "invalid_input"
    if isinstance(exc, FileNotFoundError):
        return "unavailable"
    if isinstance(exc, RuntimeError):
        return "operation_failed"
    return "internal_error"


async def _invoke(tool: str, fn: ToolCallback) -> dict[str, object]:
    request_id = _request_id()
    started = time.monotonic()
    status = "error"
    result_label = "error"
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(fn, request_id),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
        status = "completed"
        result_label = "success" if result.get("ok") is not False else "negative"
        return _safe_result(result)
    except Exception as exc:  # boundary: return only stable, sanitized error data
        error_payload: dict[str, object] = {
            "ok": False,
            "error": ToolError(
                code=_error_code(exc),
                message=sanitize_disclosure_text(exc),
                request_id=request_id,
            ).as_dict(),
        }
        return _safe_result(error_payload)
    finally:
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        timestamp = datetime.now(timezone.utc).isoformat()
        logging.getLogger("cybercore.mcp.audit").info(
            "timestamp=%s tool=%s request_id=%s result=%s status=%s duration_ms=%s",
            timestamp,
            tool,
            request_id,
            result_label,
            status,
            duration_ms,
        )


def capability_manifest() -> dict[str, object]:
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": ["stdio"],
        "mode": "read_only",
        "tools": list(AVAILABLE_TOOLS),
        "unavailable_on_canonical_main": list(UNAVAILABLE_WORLD_MODEL_TOOLS),
        "mutation": {"supported": False, "approval_bypass": False},
        "limits": {
            "input_bytes": MAX_TEXT_INPUT,
            "response_bytes": MAX_RESPONSE_BYTES,
            "tool_timeout_seconds": TOOL_TIMEOUT_SECONDS,
        },
    }


def build_server(repo: str | None = None) -> MCPServer:
    paths = RuntimePaths.discover(repo)
    server = MCPServer(SERVER_NAME)

    @server.tool(name="cybercore.capabilities", annotations=READ_ONLY_ANNOTATIONS)
    async def capabilities() -> dict[str, object]:
        """Return the explicit fail-closed CyberCore MCP capability manifest."""

        def run(rid: str) -> dict[str, object]:
            return {"ok": True, "request_id": rid, **capability_manifest()}

        return await _invoke("cybercore.capabilities", run)

    @server.tool(name="cybercore.status", annotations=READ_ONLY_ANNOTATIONS)
    async def status() -> dict[str, object]:
        """Return sanitized local CyberCore runtime status without mutation."""

        def run(rid: str) -> dict[str, object]:
            lines = [sanitize_disclosure_text(line) for line in status_lines(paths)]
            return {"ok": True, "request_id": rid, "status": lines}

        return await _invoke("cybercore.status", run)

    @server.tool(name="cybercore.project_context", annotations=READ_ONLY_ANNOTATIONS)
    async def project_context() -> dict[str, object]:
        """Return trusted repository context through the canonical disclosure policy."""

        def run(rid: str) -> dict[str, object]:
            context = collect_trusted_operation_context(
                paths.repo, operation="mcp_project_context", risk="low"
            )
            return {
                "ok": True,
                "request_id": rid,
                "context": disclose_context_payload(
                    context.as_dict(), mode=DisclosureMode.STANDARD
                ),
            }

        return await _invoke("cybercore.project_context", run)

    @server.tool(name="cybercore.verify.repository", annotations=READ_ONLY_ANNOTATIONS)
    async def verify_repository() -> dict[str, object]:
        """Verify repository identity against canonical CyberCore policy."""

        def run(rid: str) -> dict[str, object]:
            result = evaluate_repository_identity_policy(paths.repo)
            return {
                "ok": result.compliant,
                "request_id": rid,
                "verification": disclosed_repository_identity_policy_payload(result),
            }

        return await _invoke("cybercore.verify.repository", run)

    @server.tool(name="cybercore.verify.runtime", annotations=READ_ONLY_ANNOTATIONS)
    async def verify_runtime() -> dict[str, object]:
        """Run read-only CyberCore runtime dependency checks."""

        def run(rid: str) -> dict[str, object]:
            checks = [
                {
                    "name": item.name,
                    "state": str(item.state),
                    "detail": sanitize_disclosure_text(item.detail),
                }
                for item in run_doctor(paths)
            ]
            return {
                "ok": all(item["state"].lower().endswith("ok") for item in checks),
                "request_id": rid,
                "checks": checks,
            }

        return await _invoke("cybercore.verify.runtime", run)

    @server.tool(name="cybercore.ccl.validate", annotations=READ_ONLY_ANNOTATIONS)
    async def ccl_validate(record_json: str) -> dict[str, object]:
        """Validate one bounded CCL JSON record against canonical schemas."""

        def run(rid: str) -> dict[str, object]:
            raw = _bounded_text(record_json, name="record_json")
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("CCL record must be a JSON object")
            result = CCLValidator.from_repo(paths.repo).validate(record)
            return {"ok": result.valid, "request_id": rid, "validation": result.as_dict()}

        return await _invoke("cybercore.ccl.validate", run)

    @server.tool(name="cybercore.plan.change", annotations=READ_ONLY_ANNOTATIONS)
    async def plan_change(goal: str) -> dict[str, object]:
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
                    "required_sequence": [
                        "observe",
                        "evidence",
                        "reason",
                        "plan",
                        "explicit_approval",
                        "apply",
                        "verify",
                    ],
                },
            }

        return await _invoke("cybercore.plan.change", run)

    return server


def serve(repo: str | None = None) -> None:
    build_server(repo).run(transport="stdio")
