# WB-0028 Staging Plan Validator — Candidate Evidence

Date: 2026-08-20
Repository: `cyberDJs/CyberCore`
Work block: `WB-0028`
Pull request: `#45`
Branch: `feat/wb-0028-staging-plan-validator`
Canonical base: `main@883abf1126c87c07c9a65f8cc59c3e2582048c92`
Status: `CANDIDATE — HOSTED VERIFICATION PENDING`

## Authorized scope

The operator explicitly authorized:

- post-PR44 state reconciliation;
- disabled/manual staging workflow;
- deployment manifest + target validator;
- fail-closed tests and guardrails;
- hosted CI + CodeQL + review;
- progression only to `READY_FOR_MERGE`.

The authorization does **not** include merge of PR #45, InterServer remote write, credential access, provider mutation, or production deployment.

## Implementation candidate

PR #45 currently adds:

- `src/cybercore/deployment/staging.py` — fail-closed target assessment and manifest generation;
- `src/cybercore/deployment/__init__.py` — deployment package boundary without eager execution imports;
- `.github/workflows/staging-plan.yml` — manual-only local plan workflow;
- `tests/test_staging_deployment.py` — target/manifest/authority regressions;
- expanded `tests/test_ci_foundation.py` workflow security contract;
- PyYAML as a runtime dependency because the shipped validator reads the canonical target YAML.

## Local SandCloud evidence

Session: `20260820T064600Z-CyberCore-WB0028-staging-slice`

Observed locally in the isolated runner:

- focused validator tests: **12 passed**;
- validator + workflow-contract prototype tests: **24 passed**;
- Python compile check: PASS for prototype sources/tests;
- `plan_only` against the current draft InterServer target: manifest created with `plan_status=BLOCKED` and `remote_write_allowed=false`;
- unresolved gates were explicitly enumerated;
- `dry_run` against the current draft target: blocked with exit code `2`;
- no network/provider connection was attempted by the validator.

## Local runner limitation

A direct GitHub network check failed because the isolated runner could not resolve `github.com`:

```text
fatal: unable to access 'https://github.com/cyberDJs/CyberCore.git/': Could not resolve host: github.com
```

Therefore local full-repository verification is **UNKNOWN**, not PASS. Hosted GitHub Actions CI/CodeQL are the required canonical verification for this candidate.

## Safety findings

Verified from the candidate design and local prototype:

- remote modes are rejected by Python API;
- every generated manifest hard-codes `remote_write_allowed=false`;
- current unresolved target remains blocked;
- production domain reuse is rejected;
- production/provider mutation flags cannot be weakened;
- obvious secret-value fields are rejected from target metadata;
- secret alias metadata remains permitted;
- unapproved secret stores are rejected;
- evidence output paths reject absolute/path-traversal destinations;
- manual workflow exposes no remote mode or secret context.

## Expected hosted gates

PR #45 must not move to `READY_FOR_MERGE` until the exact final head has:

- CI success across Python 3.11–3.14;
- Ruff success;
- Pyright success;
- package build/wheel smoke success;
- CodeQL success;
- no unresolved material review thread;
- verified base/head identity and `main` drift check.

## Stop line

Stop before:

- merging PR #45 without new merge authorization;
- executing `staging_apply`;
- connecting to InterServer;
- reading or writing credential values;
- changing DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or production;
- weakening tests or branch/security gates to make the candidate pass.

## Rollback

PR #45 is branch-isolated. Revert or close the PR to remove the candidate. No remote-system rollback is required because no remote mutation is in scope.
