# Self-Deployment Authority Boundary v0

Date: 2026-08-19
Work block: `WB-0028`

## Authority levels

| Level | Description | Current authority |
|---|---|---|
| Repository branch writes | Non-canonical branch docs/state changes | Allowed |
| PR creation | Open reviewable branch against `main` | Allowed |
| PR merge | Merge into canonical `main` | Requires explicit Jan Kočí authorization and green checks |
| Staging plan | Produce non-secret plan/manifest | Allowed |
| Staging dry run | Validate locally/no remote write | Allowed after workflow exists |
| Staging apply | Remote write to InterServer staging | Requires explicit Jan Kočí authorization and verified staging target |
| Production apply | Production remote write | Not allowed in WB-0028 |

## Standing denial

No autonomous process may treat staging success as production approval.

## Human approval policy

External human review is optional for documentation/state-only non-production PRs.

Explicit operator authorization from Jan Kočí remains required for:

- PR merge;
- first live staging remote write;
- any production, provider, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or secret operation.