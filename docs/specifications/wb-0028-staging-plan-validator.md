# WB-0028 Staging Plan Validator

Status: Candidate implementation
Date: 2026-08-20
Work block: `WB-0028`
Related ADR: `ADR-0006 — Self-Deployment Staging Boundary` (Accepted)
Pull request: `#45`

## Purpose

Provide a deterministic, fail-closed local planning boundary for CyberCore staging deployment work without granting any remote-write authority.

This slice turns the accepted ADR-0006 boundary into executable validation for two local-only modes:

- `plan_only` — inspect the non-secret staging target contract and emit a safe manifest even when runtime gates remain unresolved;
- `dry_run` — validate that all modeled non-secret gates are resolved before declaring a local dry-run contract ready.

This slice does **not** implement or authorize `staging_apply`.

## Inputs

The validator consumes:

- `.cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml`;
- canonical repository identity;
- source branch;
- exact 40-character source commit SHA;
- non-secret artifact identity;
- run identifier;
- safe relative evidence destination;
- local mode: `plan_only` or `dry_run`.

It does not consume secret values, provider credentials, SSH/SFTP sessions, remote APIs, or production configuration.

## Target invariants

The validator fails closed unless all structural safety invariants hold:

1. target id is exactly `interserver-shared-hosting-staging`;
2. environment class is exactly `staging`;
3. production mutation remains false;
4. production credentials remain denied;
5. provider mutation without explicit approval remains false;
6. live staging deployment remains `blocked` in this slice;
7. deployment user scope remains `staging_path_only`;
8. a concrete staging URL may not resolve to a denied production domain;
9. approved secret locations remain limited to the current governance allowlist;
10. fields that would store obvious secret values are rejected from target metadata.

Secret aliases are metadata and are allowed; secret values are not.

## Runtime gates

The current target remains intentionally unresolved. The validator reports or blocks on:

- staging URL/domain;
- staging document root;
- verified deployment capability;
- verified secret-alias availability status;
- verified rollback mode;
- verified effect-verifier status.

`plan_only` may emit a manifest with these unresolved gates. Such a manifest has:

- `plan_status: BLOCKED`;
- `remote_write_allowed: false`.

`dry_run` fails with a non-zero exit while any gate remains unresolved.

Even when all modeled gates are locally verified, `dry_run` retains `remote_write_allowed: false`.

## Manifest contract

A generated manifest contains only non-secret planning evidence:

- run id;
- canonical repository;
- source branch;
- source commit;
- artifact identity;
- staging target id;
- local deploy mode;
- plan status;
- safe evidence destination;
- `remote_write_allowed: false`;
- unresolved gate identifiers.

The manifest is evidence, not authority.

## Hard remote-write boundary

The Python API rejects:

- `staging_apply`;
- `staging_apply_after_explicit_operator_approval`;
- any mode outside `plan_only | dry_run`.

A later remote-write implementation requires a separate authorized slice after all target gates and a fresh explicit operator authorization pass.

## GitHub Actions workflow contract

`.github/workflows/staging-plan.yml` is intentionally local-only:

- trigger: `workflow_dispatch` only;
- permissions: `contents: read` only;
- modes exposed: `plan_only`, `dry_run` only;
- target exposed: `interserver-shared-hosting-staging` only;
- checkout credentials are not persisted;
- actions are pinned by full commit SHA;
- no GitHub Environment;
- no `secrets.*` context;
- no SSH/SCP/SFTP/rsync/provider write command;
- no `staging_apply` option;
- output is a safe local plan artifact only.

The current target causes manual `dry_run` to fail closed until target gates are verified. That is expected behavior.

## Verification requirements

Before PR #45 can reach `READY_FOR_MERGE`:

- Python 3.11–3.14 tests pass;
- Ruff lint and format checks pass;
- Pyright passes;
- package build and installed-wheel smoke pass;
- CodeQL passes;
- workflow security regression tests pass;
- valid review findings are remediated;
- `main` has not drifted unexpectedly from the reviewed base;
- no remote mutation has occurred.

## Rollback

Normal revert of PR #45 restores the prior documentation-only staging foundation. No remote environment rollback is required because this slice performs no remote mutation.
