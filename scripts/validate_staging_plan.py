from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.staging import validate_staging_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CyberCore staging target and manifest")
    parser.add_argument(
        "--target",
        default=".cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml",
        help="Path to non-secret staging target contract",
    )
    parser.add_argument(
        "--manifest",
        default=".cybercore/deploy/manifests/interserver-staging-plan-only.example.yaml",
        help="Path to staging deployment manifest",
    )
    args = parser.parse_args(argv)

    result = validate_staging_plan(Path(args.target), Path(args.manifest))
    print(result.as_text())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
