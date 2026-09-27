from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import time
import uuid
from typing import Any, Protocol

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
SERVER_VERSION = "0.2.0"
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
    "cybercore.events.post",
    "cybercore.events.read",
    "cybercore.events.subscribe",
    "cybercore.presence.get",
    "cybercore.runtime.status",
    "cybercore.agent.invoke",
    "cybercore.tool.invoke",
)
READ_ONLY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True, open_world_hint=False
)
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


class CommunicationToolBackend(Protocol):
    allowed_tools: frozenset[str]

    def post_event(self, **kwargs: Any) -> Mapping[str, Any]: ...

    def read_events(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def subscribe_events(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def get_presence(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def get_runtime_status(self) -> Mapping[str, Any]: ...

    def invoke_agent(self, **kwargs: Any) -> list[dict[str, Any]]: ...

    def invoke_tool(self, **kwargs: Any) -> Mapping[str, Any]: ...


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
    return normalized in _SECRET_OUTPUT_KEYS or normalized.endswith(
        _SECRET_OUTPUT_SUFFIXES
    )


def _sanitize_output(value: object) -> object:
    if isinstance(value, str):
        return sanitize_disclosure_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if _is_secret_output_key(key)
                else _sanitize_output(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_output(item) for item in value]
    return sanitize_disclosure_text(value)


def _safe_result(payload: dict[str, object]) -> dict[str, object]:
    sanitized = _sanitize_output(payload)
    if not isinstance(sanitized, dict):
        raise TypeError("MCP result must be a JSON object")
    encoded = json.dumps(
        sanitized, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
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
    if isinstance(exc, PermissionError):
        return "forbidden"
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
        result_label = (
            "success" if result.get("ok") is not False else "negative"
        )
        return _safe_result(result)
    except Exception as exc:
        return _safe_result(
            {
                "ok": False,
                "error": ToolError(
                    _error_code(exc),
                    sanitize_disclosure_text(exc),
                    request_id,
                ).as_dict(),
            }
        )
    finally:
        logging.getLogger("cybercore.mcp.audit").info(
            "timestamp=%s tool=%s request_id=%s result=%s status=%s duration_ms=%s",
            datetime.now(timezone.utc).isoformat(),
            tool,
            request_id,
            result_label,
            status,
            round((time.monotonic() - started) * 1000, 3),
        )


def _json_object(raw: str, *, name: str) -> dict[str, Any]:
    value = json.loads(_bounded_text(raw, name=name))
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def capability_manifest(
    *, backend_configured: bool = False
) -> dict[str, object]:
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": ["stdio", "streamable-http"],
        "mode": "governed_communication",
        "tools": list(AVAILABLE_TOOLS),
        "communication_backend_configured": backend_configured,
        "mutation": {
            "communication_events": True,
            "external_effects": False,
            "approval_bypass": False,
        },
        "limits": {
            "input_bytes": MAX_TEXT_INPUT,
            "response_bytes": MAX_RESPONSE_BYTES,
            "tool_timeout_seconds": TOOL_TIMEOUT_SECONDS,
        },
    }


def build_server(
    repo: str | None = None,
    *,
    communication: CommunicationToolBackend | None = None,
) -> MCPServer:
    paths = RuntimePaths.discover(repo)
    server = MCPServer(SERVER_NAME)

    def require_backend() -> CommunicationToolBackend:
        if communication is None:
            raise RuntimeError("communication backend is not configured")
        return communication

    @server.tool(
        name="cybercore.capabilities",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def capabilities() -> dict[str, object]:
        return await _invoke(
            "cybercore.capabilities",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                **capability_manifest(
                    backend_configured=communication is not None
                ),
            },
        )

    @server.tool(
        name="cybercore.status",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def status() -> dict[str, object]:
        return await _invoke(
            "cybercore.status",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "status": [
                    sanitize_disclosure_text(line)
                    for line in status_lines(paths)
                ],
            },
        )

    @server.tool(
        name="cybercore.project_context",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def project_context() -> dict[str, object]:
        def run(rid: str) -> dict[str, object]:
            context = collect_trusted_operation_context(
                paths.repo,
                operation="mcp_project_context",
                risk="low",
            )
            return {
                "ok": True,
                "request_id": rid,
                "context": disclose_context_payload(
                    context.as_dict(), mode=DisclosureMode.STANDARD
                ),
            }

        return await _invoke("cybercore.project_context", run)

    @server.tool(
        name="cybercore.verify.repository",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def verify_repository() -> dict[str, object]:
        def run(rid: str) -> dict[str, object]:
            result = evaluate_repository_identity_policy(paths.repo)
            return {
                "ok": result.compliant,
                "request_id": rid,
                "verification": disclosed_repository_identity_policy_payload(
                    result
                ),
            }

        return await _invoke("cybercore.verify.repository", run)

    @server.tool(
        name="cybercore.verify.runtime",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def verify_runtime() -> dict[str, object]:
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
                "ok": all(
                    item["state"].lower().endswith("ok")
                    for item in checks
                ),
                "request_id": rid,
                "checks": checks,
            }

        return await _invoke("cybercore.verify.runtime", run)

    @server.tool(
        name="cybercore.ccl.validate",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def ccl_validate(record_json: str) -> dict[str, object]:
        def run(rid: str) -> dict[str, object]:
            record = _json_object(
                record_json, name="record_json"
            )
            result = CCLValidator.from_repo(paths.repo).validate(record)
            return {
                "ok": result.valid,
                "request_id": rid,
                "validation": result.as_dict(),
            }

        return await _invoke("cybercore.ccl.validate", run)

    @server.tool(
        name="cybercore.plan.change",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def plan_change(goal: str) -> dict[str, object]:
        def run(rid: str) -> dict[str, object]:
            bounded = sanitize_disclosure_text(
                _bounded_text(goal, name="goal")
            )
            return {
                "ok": True,
                "request_id": rid,
                "plan": {
                    "goal": bounded,
                    "mode": "plan_only",
                    "execution_authorized": False,
                },
            }

        return await _invoke("cybercore.plan.change", run)

    @server.tool(name="cybercore.events.post")
    async def events_post(
        room_id: str,
        session_id: str,
        target: str,
        event_type: str,
        payload_json: str = "{}",
    ) -> dict[str, object]:
        return await _invoke(
            "cybercore.events.post",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "event": dict(
                    require_backend().post_event(
                        room_id=room_id,
                        session_id=session_id,
                        target=target,
                        event_type=event_type,
                        payload=_json_object(
                            payload_json, name="payload_json"
                        ),
                    )
                ),
            },
        )

    @server.tool(
        name="cybercore.events.read",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def events_read(
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> dict[str, object]:
        return await _invoke(
            "cybercore.events.read",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "events": require_backend().read_events(
                    room_id=room_id,
                    session_id=session_id,
                    after_sequence=after_sequence,
                    limit=limit,
                ),
            },
        )

    @server.tool(
        name="cybercore.events.subscribe",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def events_subscribe(
        room_id: str,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 100,
        wait_seconds: float = 1.0,
    ) -> dict[str, object]:
        return await _invoke(
            "cybercore.events.subscribe",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "mode": "bounded_long_poll",
                "events": require_backend().subscribe_events(
                    room_id=room_id,
                    session_id=session_id,
                    after_sequence=after_sequence,
                    limit=limit,
                    wait_seconds=wait_seconds,
                ),
            },
        )

    @server.tool(
        name="cybercore.presence.get",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def presence_get(
        room_id: str, session_id: str
    ) -> dict[str, object]:
        return await _invoke(
            "cybercore.presence.get",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "presence": require_backend().get_presence(
                    room_id=room_id, session_id=session_id
                ),
            },
        )

    @server.tool(
        name="cybercore.runtime.status",
        annotations=READ_ONLY_ANNOTATIONS,
    )
    async def runtime_status() -> dict[str, object]:
        return await _invoke(
            "cybercore.runtime.status",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "runtime": dict(
                    require_backend().get_runtime_status()
                ),
            },
        )

    @server.tool(name="cybercore.agent.invoke")
    async def agent_invoke(
        room_id: str,
        session_id: str,
        target_agent: str,
        message: str,
    ) -> dict[str, object]:
        return await _invoke(
            "cybercore.agent.invoke",
            lambda rid: {
                "ok": True,
                "request_id": rid,
                "events": require_backend().invoke_agent(
                    room_id=room_id,
                    session_id=session_id,
                    target_agent=target_agent,
                    message=_bounded_text(
                        message, name="message"
                    ),
                ),
            },
        )

    @server.tool(name="cybercore.tool.invoke")
    async def tool_invoke(
        tool_name: str,
        arguments_json: str = "{}",
    ) -> dict[str, object]:
        def run(rid: str) -> dict[str, object]:
            backend = require_backend()
            if tool_name not in backend.allowed_tools:
                raise PermissionError("tool is not allowlisted")
            return {
                "ok": True,
                "request_id": rid,
                "tool": tool_name,
                "result": dict(
                    backend.invoke_tool(
                        tool_name=tool_name,
                        arguments=_json_object(
                            arguments_json,
                            name="arguments_json",
                        ),
                    )
                ),
            }

        return await _invoke("cybercore.tool.invoke", run)

    return server
