"""Governed CyberCore MCP interface."""

from __future__ import annotations


def build_server(*args, **kwargs):
    from cybercore.mcp.server import build_server as _build_server

    return _build_server(*args, **kwargs)


__all__ = ["build_server"]
