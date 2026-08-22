from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.first_write_packet import validate_first_write_packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the WB-0034 final first-write packet")
    parser.add_argument(
        "--manifest",
        default=".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml",
        help="Path to the populated WB-0034 manifest",
    )
    parser.add_argument(
        "--readiness",
        default=".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml",
        help="Path to the populated WB-0034 readiness artifact",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root whose HEAD is the exact deployment source commit",
    )
    args = parser.parse_args(argv)

    result = validate_first_write_packet(
        Path(args.manifest),
        Path(args.readiness),
        Path(args.repo_root),
    )
    print(result.as_text())
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
