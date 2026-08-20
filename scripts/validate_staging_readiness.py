from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.staging import validate_remote_write_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CyberCore staging remote-write readiness")
    parser.add_argument(
        "--readiness",
        default=".cybercore/deploy/readiness/interserver-staging-readiness.example.yaml",
        help="Path to non-secret staging readiness evidence",
    )
    parser.add_argument(
        "--expect-blocked",
        action="store_true",
        help="Return success only when the readiness gate is blocked as expected",
    )
    args = parser.parse_args(argv)

    result = validate_remote_write_readiness(Path(args.readiness))
    print(result.as_text())
    if args.expect_blocked:
        return 0 if not result.ok else 1
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
