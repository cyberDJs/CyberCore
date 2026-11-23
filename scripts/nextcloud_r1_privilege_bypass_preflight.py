#!/usr/bin/env python3
"""Issue #113: fail-closed static detection of direct systemd start bypass.

This is a repository-candidate diagnostic. It does not evaluate or change live
Polkit policy. A PASS requires a separate runtime policy and denial test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "deploy/cybercore-exec-nextcloud-r1/cybercore-exec.policy"
OPERATIONS = ROOT / "src/cybercore/execution/server/operations.py"
SERVICE = "cybercore-exec"
UNITS = (
    "cybercore-nextcloud-r1-transfer.service",
    "cybercore-nextcloud-r1-rollback.service",
)


def uncomment(text: str) -> str:
    # Conservative: strip standalone and trailing JS comments, not parse JS.
    return re.sub(r"(?m)//[^\n]*", "", text)


def assess(policy: str, operations: str) -> dict[str, object]:
    clean = uncomment(policy)
    # The bundled candidate authorizes a service identity to call systemd
    # manage-units directly. That authorization is not tied to the dispatcher
    # approval manifest and can be exercised outside the protocol handler.
    direct_grant = all(
        marker in clean
        for marker in (
            "polkit.Result.YES",
            "org.freedesktop.systemd1.manage-units",
            SERVICE,
            *UNITS,
        )
    )
    protected_actions = all(
        action in operations
        for action in ("nextcloud.r1.offhost.transfer", "nextcloud.r1.offhost.rollback")
    )
    concerns: list[str] = []
    if direct_grant:
        concerns.append("polkit_direct_start_not_bound_to_exact_dispatcher_approval")
    if not protected_actions:
        concerns.append("expected_governed_operation_mapping_missing")
    # A static source check is NEVER sufficient to enable privileged services.
    return {
        "issue": 113,
        "status": "BLOCKED_DIRECT_UNIT_START" if concerns else "STATIC_CANDIDATE_REQUIRES_RUNTIME_PROOF",
        "concerns": concerns,
        "direct_privileged_start_grant_detected": direct_grant,
        "runtime_denial_verified": False,
        "activation_approved": False,
        "activation_performed": False,
    }


def exit_code(result: dict[str, object]) -> int:
    """Fail closed unless a future runtime verifier emits an explicit PASS."""
    status = str(result.get("status", ""))
    if status == "RUNTIME_VERIFIED_PASS":
        return 0
    if status.startswith("BLOCKED"):
        return 2
    return 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=POLICY)
    parser.add_argument("--operations", type=Path, default=OPERATIONS)
    args = parser.parse_args()
    try:
        result = assess(
            args.policy.read_text(encoding="utf-8"),
            args.operations.read_text(encoding="utf-8"),
        )
    except (OSError, UnicodeError) as exc:
        result = {
            "issue": 113,
            "status": "BLOCKED_UNREADABLE_INPUT",
            "reason": str(exc),
            "activation_approved": False,
            "activation_performed": False,
        }
    print(json.dumps(result, sort_keys=True))
    return exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
