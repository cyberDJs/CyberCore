from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import time

from mcp import Client, StdioServerParameters
from mcp.client.stdio import get_default_environment
import pytest

import cybercore.mcp.server as mcp_server
from cybercore.mcp.server import (
    AVAILABLE_TOOLS,
    MAX_RESPONSE_BYTES,
    MAX_TEXT_INPUT,
    _bounded_text,
    _invoke,
    _safe_result,
    capability_manifest,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _structured(result) -> dict[str, object]:
    payload = result.structured_content
    assert isinstance(payload, dict)
    return payload


def test_capabilities_are_explicitly_read_only() -> None:
    manifest = capability_manifest()
    assert manifest["mode"] == "read_only"
    assert manifest["mutation"] == {"supported": False, "approval_bypass": False}
    assert "run_shell" not in json.dumps(manifest)


def test_capabilities_publish_small_allowlist() -> None:
    tools = capability_manifest()["tools"]
    assert isinstance(tools, list)
    assert tools == list(AVAILABLE_TOOLS)
    assert len(tools) == 7
    assert all(name.startswith("cybercore.") for name in tools)


def test_unintegrated_world_model_tools_are_not_claimed_available() -> None:
    manifest = capability_manifest()
    unavailable = manifest["unavailable_on_canonical_main"]
    assert "cybercore.entities.search" in unavailable
    assert "cybercore.evidence.search" in unavailable
    assert "cybercore.findings.list" in unavailable


def test_bounded_text_rejects_oversized_input() -> None:
    oversized = "x" * (MAX_TEXT_INPUT + 1)
    with pytest.raises(ValueError, match="exceeds"):
        _bounded_text(oversized, name="value")


def test_safe_result_redacts_secret_keys_assignments_and_paths() -> None:
    payload = {
        "token": "literal-token-value",
        "nested": {"access_token": "nested-token-value"},
        "message": (
            "password=hunter2 at /private/cybercore/path from "
            "https://user:secret@example.test/repo"
        ),
    }

    sanitized = _safe_result(payload)
    rendered = json.dumps(sanitized)

    assert sanitized["token"] == "[REDACTED]"
    assert "literal-token-value" not in rendered
    assert "nested-token-value" not in rendered
    assert "hunter2" not in rendered
    assert "/private/cybercore/path" not in rendered
    assert "user:secret" not in rendered


def test_safe_result_rejects_oversized_response() -> None:
    with pytest.raises(ValueError, match="response exceeds"):
        _safe_result({"data": "x" * (MAX_RESPONSE_BYTES + 1)})


def test_tool_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "TOOL_TIMEOUT_SECONDS", 0.01)

    def slow(request_id: str) -> dict[str, object]:
        time.sleep(0.05)
        return {"ok": True, "request_id": request_id}

    result = asyncio.run(_invoke("cybercore.test.timeout", slow))
    assert result["ok"] is False
    error = result["error"]
    assert isinstance(error, dict)
    assert error["code"] == "timeout"


def test_stdio_transport_does_not_inherit_arbitrary_parent_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBERCORE_TEST_SECRET", "must-not-cross-stdio-boundary")
    child_environment = get_default_environment()

    assert "PATH" in child_environment
    assert "CYBERCORE_TEST_SECRET" not in child_environment
    assert "must-not-cross-stdio-boundary" not in json.dumps(child_environment)


async def _exercise_stdio_server(repo: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "cybercore.mcp", "--repo", str(repo), "serve"],
        cwd=str(repo),
    )

    async with Client(params) as client:
        listed = await client.list_tools()
        names = {tool.name for tool in listed.tools}
        assert names == set(AVAILABLE_TOOLS)

        for tool in listed.tools:
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True
            assert tool.annotations.open_world_hint is False

        capabilities = await client.call_tool("cybercore.capabilities", {})
        assert capabilities.is_error is False
        capability_payload = _structured(capabilities)
        assert capability_payload["ok"] is True
        assert capability_payload["mode"] == "read_only"

        repository = await client.call_tool("cybercore.verify.repository", {})
        assert repository.is_error is False
        repository_payload = _structured(repository)
        assert repository_payload["ok"] is True

        context = await client.call_tool("cybercore.project_context", {})
        assert context.is_error is False
        context_payload = _structured(context)
        assert context_payload["ok"] is True
        assert str(repo) not in json.dumps(context_payload)

        status = await client.call_tool("cybercore.status", {})
        assert status.is_error is False
        status_payload = _structured(status)
        assert str(repo) not in json.dumps(status_payload)

        malicious_goal = (
            "inspect ../../etc/passwd; token=super-secret; "
            "https://user:password@example.test/private"
        )
        plan = await client.call_tool("cybercore.plan.change", {"goal": malicious_goal})
        assert plan.is_error is False
        plan_payload = _structured(plan)
        rendered_plan = json.dumps(plan_payload)
        plan_body = plan_payload["plan"]
        assert isinstance(plan_body, dict)
        assert plan_body["execution_authorized"] is False
        assert "../../etc/passwd" in str(plan_body["goal"])
        assert "super-secret" not in rendered_plan
        assert "user:password" not in rendered_plan

        malformed = await client.call_tool("cybercore.ccl.validate", {"record_json": "{"})
        assert malformed.is_error is False
        malformed_payload = _structured(malformed)
        assert malformed_payload["ok"] is False
        malformed_error = malformed_payload["error"]
        assert isinstance(malformed_error, dict)
        assert malformed_error["code"] == "invalid_json"

        invalid_tool = await client.call_tool("run_shell", {"command": "id"})
        assert invalid_tool.is_error is True

        unsupported = await client.call_tool("cybercore.entities.search", {"query": "server"})
        assert unsupported.is_error is True


def test_mcp_client_to_stdio_tools_list_and_call() -> None:
    asyncio.run(_exercise_stdio_server(_repo_root()))


def test_cli_doctor_checks_protocol_tools_and_disclosure() -> None:
    repo = _repo_root()
    completed = subprocess.run(
        [sys.executable, "-m", "cybercore.mcp", "--repo", str(repo), "doctor"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    for name in (
        "python_package",
        "repository",
        "schemas",
        "disclosure",
        "mcp_protocol",
        "tool_registration",
        "capabilities_call",
    ):
        assert payload[name] is True


def test_capability_manifest_contains_no_secret_values() -> None:
    rendered = json.dumps(capability_manifest()).lower()
    for marker in ("api_key=", "password=", "token=", "private_key"):
        assert marker not in rendered
