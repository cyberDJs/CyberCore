# WB-0028 Value Gate

Date: 2026-08-19

## Problem

CyberCore can already manage branch, PR, CI, review, and merge flow, but it lacks a defined safe boundary for self-deployment.

## Beneficiary

Jan Kočí / CyberCore operations, because the system can move toward faster development without uncontrolled production risk.

## Expected improvement

- Clear staging-only self-deployment path.
- Explicit InterServer staging target contract.
- No secret leakage.
- No production mutation.
- A clean next slice for plan-only/dry-run workflow implementation.

## Alternatives considered

1. Add deploy workflow immediately: rejected until target and rollback are verified.
2. Keep only manual deployment: rejected because it does not advance self-deployment capability.
3. Create design and target contract first: selected.

## Result

`VALUE_GATE=PASS` for documentation/state scaffolding.