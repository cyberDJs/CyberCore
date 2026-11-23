"""Inert SO_PEERCRED adapter for issue #113 one-shot broker core.

No bind/listen daemon, no root service, no production runner and no entrypoint.
Only an accepted AF_UNIX stream socket can be passed by a future trusted owner.
"""
from __future__ import annotations

import json
import os
import socket
import struct
from typing import Callable

from cybercore.execution.nextcloud_r1_broker_core import Rejected, Request

MAX_REQUEST_BYTES = 4096
_FIELDS = frozenset({
    "operation_id", "operation", "target_id", "plan_id",
    "plan_revision", "authorization_reference",
})


def kernel_peer_uid(conn: socket.socket) -> int:
    """Retrieve the peer UID from Linux kernel metadata, never request text."""
    if conn.family != socket.AF_UNIX or conn.type & 0xF != socket.SOCK_STREAM:
        raise Rejected("trusted AF_UNIX stream required")
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    if len(raw) != struct.calcsize("3i"):
        raise Rejected("invalid kernel peer credentials")
    pid, uid, gid = struct.unpack("3i", raw)
    if pid <= 0 or uid < 0 or gid < 0:
        raise Rejected("invalid kernel peer identity")
    return uid


def read_request(conn: socket.socket) -> Request:
    """One bounded newline-terminated JSON request; no trailing frames."""
    data = bytearray()
    while len(data) <= MAX_REQUEST_BYTES:
        chunk = conn.recv(min(512, MAX_REQUEST_BYTES + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if b"\n" in chunk:
            break
    if len(data) > MAX_REQUEST_BYTES or data.count(b"\n") != 1 or not data.endswith(b"\n"):
        raise Rejected("request framing invalid or oversized")
    try:
        fields = json.loads(data[:-1].decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Rejected("invalid JSON request") from exc
    if not isinstance(fields, dict) or fields.keys() != _FIELDS:
        raise Rejected("unexpected request schema")
    if any(not isinstance(value, str) or not value or len(value) > 256
           for value in fields.values()):
        raise Rejected("invalid request value")
    return Request(**fields)


def handle_connection(
    conn: socket.socket,
    *,
    expected_peer_uid: int,
    dispatch: Callable[[Request, int], dict[str, object]],
) -> dict[str, object]:
    """Unprivileged synthetic adapter: dispatch receives kernel uid only.

    The callback is injected; this module never chooses a privileged command.
    A future service must ensure its root-owned socket and authorization policy.
    """
    uid = kernel_peer_uid(conn)
    if isinstance(expected_peer_uid, bool) or expected_peer_uid <= 0 or uid != expected_peer_uid:
        raise Rejected("peer identity not permitted")
    request = read_request(conn)
    return dispatch(request, uid)
