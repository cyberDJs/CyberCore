# WB-0028 — Self-Deployment Staging Loop v0

Status: Active candidate
Activated by: Jan Kočí operator authorization / CASER
Date: 2026-08-19
Canonical repository: `cyberDJs/CyberCore`
Target branch: `feat/wb-0028-self-deploy-staging-loop`

## Goal

Define the first safe CyberCore self-deployment loop for a non-production InterServer shared-hosting staging target.

The target capability is:

```text
change request -> branch -> implementation -> tests -> PR -> review gates -> staging deployment plan -> staging deploy -> effect verification -> evidence receipt
```

This work block starts the self-deployment layer without granting production mutation authority and without storing plaintext secrets in ordinary evidence, GitHub code, Google Drive, Slack, chat, CASER documents, or ChatGPT Library.

## Current source-of-truth context

- GitHub `main` is the canonical product state.
- PR #38 is merged and records PR #37 post-merge reconciliation.
- `OPS-0001` remains the active security baseline record and its unresolved security blockers remain live gates.
- The operator selected InterServer shared hosting as the first staging target.
- Staging deployment authority is limited to non-production staging and still requires target-specific capability verification before any live remote mutation.

## Scope

### In scope

- Self-deployment control-plane architecture for staging only.
- InterServer shared-hosting staging target specification without secrets.
- Manual preparation runbook for staging target creation and secret alias setup.
- Deployment evidence and effect-verification model.
- Rollback model for shared-hosting constraints.
- State transition from PR #38 reconciliation to WB-0028 active candidate.
- Draft PR and documentation/evidence needed for review.

### Out of scope without separate explicit approval

- Production deployment.
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutations.
- Creating, rotating, reading, or storing plaintext secrets.
- Running a live deploy against InterServer.
- Accepting ADR-0004 or any governance policy change.
- Disabling required checks or weakening branch protection.

## Safety gates

Live staging deployment remains blocked until all are true:

1. staging target identity is verified and recorded without secrets;
2. staging host/path/user are non-production and isolated from production;
3. replacement credentials are stored only in an OS-backed secret store, GitHub Environment secret, or approved external vault;
4. no production credential is reused for staging;
5. rollback path is verified or a limited no-overwrite deploy mode is used;
6. effect verifier is defined before deployment;
7. deployment receipt format is ready before deployment;
8. Jan Kočí gives explicit approval for the first live staging deploy attempt.

## Required outputs

1. `docs/architecture/self-deployment-staging-loop-v0.md`
2. `.cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml`
3. `docs/runbooks/interserver-staging-self-deploy-v0.md`
4. `docs/audits/2026-08-19-wb0028-self-deployment-kickoff.md`
5. ADR candidate for the staging boundary, if architecture impact is material.
6. Updated project state/kernel for WB-0028.

## Initial design decision

The first version is **plan-first and staging-only**. It may define the deployment loop and required configuration, but it must not perform a remote write until the staging target, secret aliases, rollback method, and effect verifier are verified.

## Exit criteria

- A staging self-deployment architecture exists and is reviewable.
- The InterServer staging target spec contains no plaintext secrets.
- The runbook lists all manual/provider preparation steps and required approvals.
- Live deploy is either blocked with explicit missing gates or authorized with evidence.
- CI and CodeQL pass.
- Manual AI review passes.
- Merge is explicitly authorized by Jan Kočí.

## Expected next work

If WB-0028 lands as documentation/state scaffolding, the next implementation slice can add a disabled/manual GitHub Actions staging workflow and a local manifest validator. The workflow must remain staging-only and must fail closed when required secret aliases or target identifiers are missing.