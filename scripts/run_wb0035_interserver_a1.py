from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from cybercore.interserver_a1 import A1ProbeError, run_live_a1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the WB-0035 InterServer A1 catalog + quote probe without ordering"
    )
    parser.add_argument(
        "--out-dir",
        default="dist/wb0035-a1",
        help="Directory for sanitized A1 catalog/quote evidence",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("INTERSERVER_API_KEY", "")
    if not api_key:
        print("WB-0035 A1 BLOCKED: runtime secret alias INTERSERVER_API_KEY is not available")
        return 78

    try:
        catalog_path, quote_path = run_live_a1(api_key, Path(args.out_dir))
    except A1ProbeError as exc:
        print(f"WB-0035 A1 BLOCKED: {exc}")
        return 1

    print("WB-0035 A1 PASS: authenticated catalog and pure quote validation completed")
    print(f"sanitized_catalog={catalog_path}")
    print(f"sanitized_quote={quote_path}")
    print("order_performed=false")
    print("payment_performed=false")
    print("provider_mutation_performed=false")
    print("secret_values_recorded=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
