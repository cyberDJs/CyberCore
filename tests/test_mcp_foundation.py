from __future__ import annotations

import json

from cybercore.mcp.server import MAX_TEXT_INPUT, _bounded_text, capability_manifest


def test_capabilities_are_explicitly_read_only() -> None:
    manifest = capability_manifest()
    assert manifest["mode"] == "read_only"
    assert manifest["mutation"] == {"supported": False, "approval_bypass": False}
    assert "run_shell" not in json.dumps(manifest)


def test_capabilities_publish_small_allowlist() -> None:
    tools = capability_manifest()["tools"]
    assert isinstance(tools, list)
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
    try:
        _bounded_text(oversized, name="value")
    except ValueError as exc:
        assert "exceeds" in str(exc)
    else:
        raise AssertionError("oversized MCP input was accepted")


def test_capability_manifest_contains_no_secret_values() -> None:
    rendered = json.dumps(capability_manifest()).lower()
    for marker in ("api_key=", "password=", "token=", "private_key"):
        assert marker not in rendered
