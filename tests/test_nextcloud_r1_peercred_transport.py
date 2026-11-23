"""Synthetic real-kernel SO_PEERCRED tests for inert #113 transport adapter."""

from __future__ import annotations

import json
import os
import socket
import unittest

from cybercore.execution.nextcloud_r1_broker_core import Rejected
from cybercore.execution.nextcloud_r1_peercred_transport import (
    MAX_REQUEST_BYTES,
    handle_connection,
    kernel_peer_uid,
    read_request,
)


def payload(**overrides):
    value = {
        "operation_id": "op-synthetic",
        "operation": "nextcloud.r1.offhost.transfer",
        "target_id": "cyberskills-vps",
        "plan_id": "p",
        "plan_revision": "1",
        "authorization_reference": "no-real-approval",
    }
    value.update(overrides)
    return value


class PeercredTransportTests(unittest.TestCase):
    def setUp(self):
        self.client, self.server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(self.client.close)
        self.addCleanup(self.server.close)
        self.client.settimeout(1)
        self.server.settimeout(1)
        self.calls = []

    def send(self, value):
        self.client.sendall(json.dumps(value).encode() + b"\n")

    def dispatch(self, request, uid):
        self.calls.append((request, uid))
        return {"status": "SYNTHETIC_ONLY"}

    def test_real_kernel_peer_uid_then_bounded_request(self):
        self.assertEqual(kernel_peer_uid(self.server), os.getuid())
        if os.getuid() == 0:
            self.skipTest("root peer not valid service UID for this acceptance test")
        self.send(payload())
        result = handle_connection(
            self.server, expected_peer_uid=os.getuid(), dispatch=self.dispatch
        )
        self.assertEqual(result["status"], "SYNTHETIC_ONLY")
        self.assertEqual(self.calls[0][1], os.getuid())
        self.assertEqual(self.calls[0][0].operation_id, "op-synthetic")

    def test_wrong_peer_uid_rejected_before_dispatch(self):
        self.send(payload())
        with self.assertRaisesRegex(Rejected, "peer identity"):
            handle_connection(
                self.server, expected_peer_uid=os.getuid() + 1, dispatch=self.dispatch
            )
        self.assertFalse(self.calls)

    def test_caller_supplied_uid_not_accepted(self):
        self.send(payload(peer_uid=995))
        with self.assertRaisesRegex(Rejected, "unexpected request schema"):
            read_request(self.server)
        self.assertFalse(self.calls)

    def test_malformed_and_extra_framing_rejected(self):
        self.client.sendall(b"not json\n")
        with self.assertRaisesRegex(Rejected, "invalid JSON"):
            read_request(self.server)

    def test_multiple_frames_in_chunk_rejected(self):
        self.client.sendall(b"{}\n{}\n")
        with self.assertRaisesRegex(Rejected, "framing"):
            read_request(self.server)

    def test_missing_line_ending_rejected(self):
        self.client.sendall(json.dumps(payload()).encode())
        self.client.shutdown(socket.SHUT_WR)
        with self.assertRaisesRegex(Rejected, "framing"):
            read_request(self.server)

    def test_oversize_rejected(self):
        self.client.sendall(b"x" * (MAX_REQUEST_BYTES + 1))
        with self.assertRaisesRegex(Rejected, "framing"):
            read_request(self.server)

    def test_nonunix_socket_denied(self):
        class NotUnix:
            family = socket.AF_INET
            type = socket.SOCK_STREAM

        with self.assertRaisesRegex(Rejected, "AF_UNIX"):
            kernel_peer_uid(NotUnix())


if __name__ == "__main__":
    unittest.main()
