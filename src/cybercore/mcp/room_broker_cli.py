from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
from threading import Event

from cybercore.mcp.room_broker import build_cyberdjs_room_broker_runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyberdjs-room-broker",
        description="Single-writer CyberDJs Room runtime broker",
    )
    parser.add_argument(
        "--log-path",
        default=os.environ.get("CYBERDJS_ROOM_LOG_PATH"),
    )
    parser.add_argument(
        "--socket-dir",
        default=os.environ.get(
            "CYBERDJS_ROOM_SOCKET_DIR",
            "/run/cyberhive/private/cyberdjs-room",
        ),
    )
    parser.add_argument(
        "--room-id",
        default=os.environ.get("CYBERDJS_ROOM_ID", "cyberdjs-main"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.log_path:
        raise SystemExit("--log-path or CYBERDJS_ROOM_LOG_PATH is required")

    runtime = build_cyberdjs_room_broker_runtime(
        Path(args.log_path),
        socket_dir=Path(args.socket_dir),
        room_id=args.room_id,
        slack_webhook_url=os.environ.get("CYBERDJS_SLACK_WAKE_WEBHOOK_URL"),
    )
    stopped = Event()

    def request_stop(signum: int, frame: object) -> None:
        del signum, frame
        stopped.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    runtime.start()
    try:
        stopped.wait()
    finally:
        runtime.close()
    return 0
