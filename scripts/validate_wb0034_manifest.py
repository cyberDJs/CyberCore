from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.first_write_manifest import validate_first_write_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the WB-0034 first-write manifest")
    parser.add_argument(
        "--manifest",
        default=".cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml",
        help="Path to the WB-0034 plan-only manifest",
    )
    args = parser.parse_args(argv)

    result = validate_first_write_manifest(Path(args.manifest))
    print(result.as_text())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
