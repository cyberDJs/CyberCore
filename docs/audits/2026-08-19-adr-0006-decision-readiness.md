# ADR-0006 Decision Readiness Review

Date: 2026-08-19
Decision date: 2026-08-20
Decision: `ADR-0006 — Self-Deployment Staging Boundary`
Work block: `WB-0028`
Review state: `DECIDED`
Recommendation: `ACCEPT`
Operator decision: `ACCEPTED`
Authorized by: Jan Kočí

## Executive verdict

ADR-0006 was explicitly accepted by Jan Kočí on 2026-08-20.

The ADR makes a governance and architecture decision, not an implementation claim: CyberCore self-deployment starts behind a staging-only boundary, remote staging mutation requires explicit operator authorization, production promotion remains separately gated, and secrets remain outside repository/chat/evidence stores.

The currently unknown InterServer deployment mechanism (`SSH/rsync`, `SFTP`, or provider-native) does not block the accepted architecture. It remains an implementation preflight gate before any `staging_apply` action.

## Evidence reviewed

- `docs/adr/0006-self-deployment-staging-boundary.md`
- `docs/architecture/self-deployment-staging-loop-v0.md`
- `.cybercore/deploy/staging-targets/interserver-shared-hosting-staging.yaml`
- `docs/runbooks/interserver-staging-self-deploy-v0.md`
- `.cybercore/project.yaml`
- `PROJECT_STATE.md`
- merged PR #39 staging-foundation evidence
- merged PR #40 / accepted ADR-0005 LangGraph boundary
- merged PR #41 trusted source-ingest boundary
- merged PR #43 ADR identifier reconciliation

Canonical review base before PR #44 merge: `main@4ca00fb7e1a6b618746afb2045e230a1763256e4`.

## Decision-quality assessment

### Distinct options reviewed

1. **Accept ADR-0006** — establish staging-only self-deployment as the governed first step. **Selected.**
2. **Defer ADR-0006** — keep all self-deployment design as non-authoritative draft material.
3. **Reject ADR-0006** — prohibit the current self-deployment direction and require a new architecture decision before further work.

Direct production-first automation was not treated as a viable option because it conflicts with existing CyberCore governance and explicit production-mutation boundaries.

### Evidence and assumptions

Verified:

- the staging architecture separates plan/dry-run/apply modes;
- production mutation remains explicitly outside the v0 boundary;
- the target contract contains no plaintext secret values;
- the runbook requires target isolation, rollback, effect verification, and operator authorization;
- LG-0001/LG-0002 are read-only orchestration/source-binding support and do not grant mutation authority;
- ADR-0005 is uniquely assigned to the accepted LangGraph decision after PR #43;
- active WB-0028 governance references have been reconciled to ADR-0006 before merge.

Still intentionally unknown:

- actual InterServer staging URL/path;
- actual deployment protocol/capability;
- actual staging-only account/identity;
- actual secret aliases present in approved storage;
- actual rollback mode supported by the hosting environment;
- actual health/effect-verifier endpoint.

These unknowns block **remote execution**, not the accepted staging-first architectural decision.

## Risks and controls

| Risk | Control | Residual state |
|---|---|---|
| Staging accidentally points at production | explicit target identity/path preflight; production domains listed as denied boundary | blocked until verified |
| Production credential reused for staging | separate staging identity and no-reuse preflight | blocked until verified |
| Secret leakage | aliases only in repo/docs/evidence; values only in approved secret storage | acceptable governance boundary |
| Deploy reports success but site is wrong | independent effect verifier required | blocked until verifier exists |
| No safe rollback | preferred/fallback rollback hierarchy; block nontrivial deploy without rollback | blocked until verified |
| Staging success silently becomes production approval | explicit separate production MOP + human approval | controlled |
| Orchestration bypasses authority | ADR-0005/LG-0001/LG-0002 remain non-authoritative/read-only boundaries | controlled |

## Accepted criteria

Jan Kočí accepted that:

1. self-deployment starts staging-only;
2. first remote staging write always requires explicit operator authorization;
3. production promotion is a separate decision and MOP;
4. secrets stay out of repository/chat/Drive/CASER ordinary evidence;
5. target identity, credential isolation, rollback, and effect verification remain mandatory runtime gates;
6. a successful staging run never implies production authorization.

## What acceptance does not authorize

Accepting ADR-0006 does **not** authorize:

- a live InterServer connection or remote write;
- creation/rotation/reading of credentials;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, or Nextcloud mutation;
- production deployment;
- bypass of GitHub checks, CASER governance, or effect verification;
- automatic promotion from staging to production.

## Next implementation slice

The operator separately authorized the next slice in the same 2026-08-20 instruction: a **disabled/manual staging workflow + local manifest/target validator**, with tests and hosted CI/CodeQL, ending at `READY_FOR_MERGE`.

`staging_apply` remains fail-closed and outside that authorization until target identity, secret aliases, deployment capability, rollback, effect verifier, and a fresh explicit remote-write authorization are all verified.

## Rollback / exit

If ADR-0006 is later found unsuitable, do not silently rewrite history. Mark it `Deprecated` or `Superseded` and create a replacement ADR. Until a remote-write slice is separately authorized, ADR acceptance has no production effect.
