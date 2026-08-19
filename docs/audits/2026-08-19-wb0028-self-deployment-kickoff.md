# WB-0028 Self-Deployment Kickoff

Date: 2026-08-19
Repository: `cyberDJs/CyberCore`
Branch: `feat/wb-0028-self-deploy-staging-loop`
Work block: `WB-0028 — Self-Deployment Staging Loop v0`

## Trigger

After PR #38 merged, the operator instructed CyberCore to continue development toward self-development and self-deployment.

Earlier operator choices for the self-deployment direction:

1. Complete self-development loop: design, implementation, test, PR, review, staging deployment, evidence.
2. Autonomy up to staging/preview deploy, without production.
3. First target: InterServer shared hosting staging.

## Source-of-truth classification

- GitHub `main` remains canonical product state.
- CASER-E / Google Drive remains evidence/archive/collaboration layer, not canonical product state.
- This audit is evidence for WB-0028 kickoff, not proof that InterServer staging deployment is already configured.
- InterServer staging target capability is currently `UNKNOWN_UNTIL_VERIFIED`.

## Safety position

WB-0028 may create documentation, target registry, architecture, runbook, and PR evidence.

WB-0028 must not perform live remote deployment until:

- staging target identity is verified;
- staging path is proven non-production;
- secret aliases are present in approved storage;
- rollback method is known;
- effect verifier is defined;
- Jan Kočí explicitly authorizes the first remote write.

## Current result

This kickoff creates a safe plan-first foundation for self-deployment. It does not mutate InterServer, DirectAdmin, DNS, mail, billing, VPS, production, WordPress, Nextcloud, or any secret material.