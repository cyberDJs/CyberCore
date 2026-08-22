from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.first_write import validate_first_write_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate WB-0034 first-write readiness")
    parser.add_argument(
        "--readiness",
        default=".cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml",
        help="Path to the WB-0034 non-secret readiness artifact",
    )
    parser.add_argument(
        "--expect-blocked",
        action="store_true",
        help="Return success when the schema is valid and the first write is still blocked",
    )
    args = parser.parse_args(argv)

    result = validate_first_write_readiness(Path(args.readiness))
    print(result.as_text())
    if args.expect_blocked:
        return 0 if result.schema_ok and not result.ready else 1
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
