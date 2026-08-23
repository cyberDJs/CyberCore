from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cybercore.vps_plan import validate_plan_and_quote, validate_vps_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the WB-0035 InterServer VPS plan/quote")
    parser.add_argument(
        "--plan",
        default=".cybercore/provisioning/interserver-vps-plan.example.yaml",
        help="Path to the fail-closed VPS plan",
    )
    parser.add_argument("--quote", help="Optional sanitized quote evidence YAML")
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    if args.quote:
        result = validate_plan_and_quote(plan_path, Path(args.quote))
    else:
        result = validate_vps_plan(plan_path)

    print(result.as_text())
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
