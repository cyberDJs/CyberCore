# CASER v4.1 — Release architecture and acceptance (ADR candidate)

Status: PROPOSED. Owner: CyberCore engineering. Tracking: #136.

## Decision context
CASER v4 specifies source-of-truth reconciliation, SandCloud execution receipts,
two preflight gates, independent verification and observed post-promotion effect.
Repeated CyberCore PRs #128–135 incurred avoidable formatting retries and
redundant GitHub status polling. The existing CyberCore GitHub CI is authoritative
for this repository, but is not by itself an independent security or runtime
attestation for an installed CASER skill.

## Decision
Evolve v4 incrementally, without weakening safety policy or changing authority.

1. Use three execution profiles: FAST for reversible docs/tests, STANDARD for
   ordinary implementation, CRITICAL for privileged, production, identity and
   security-boundary changes. Profiles alter test scheduling, not hard gates.
2. Require deterministic local/pre-PR Ruff formatting, lint and targeted tests;
   retain required Python 3.11–3.14, CodeQL and actual integration gates on
   protected branches.
3. Snapshot exact PR head SHA and independently recheck job-level status before
   merge. GitHub Actions run conclusion alone does not prove every required
   branch-protection check has propagated.
4. Prefer signed/provider-authenticated CI events if available; otherwise use
   bounded polling with backoff and limits. Do not add persistent automation
   or credentials without a separate security-reviewed deployment.
5. Run logically separate builder/verifier roles. For authorization, deployment
   or skill-governance edits, obtain an independent security verdict tied to
   the exact artifact, not only green CI.
6. Store a machine-readable run/handoff with source SHA, workstream, approvals,
   executed checks, incomplete checks, cost and next safe step.
7. Treat the currently installed CASER skill as a distinct provenance boundary:
   identify its canonical editable owner/source before modifying or publishing
   its SKILL.md or policies. CyberCore's main is product source of truth, not
   automatically the authoritative installed skill package.

## Components and dependencies
- CASER: orchestrates run and transitions, no unlimited background activity.
- CASER-SOURCER: source identity, evidence provenance and stale-doc detection.
- SandCloud / governed terminal: bounded isolated execution and receipts.
- GitHub: source, CI and protected PR merge; no bypass.
- CyberHIVE: real local integration contract, separately pinned.
- Team communication: #cyberdjs-room kickoff; responses are not approvals.
- Evidence/archive: CyberCore/CASER-E; not a replacement for live main.

## Rollout
Phase 0: baseline/owner and tool capability verification.
Phase 1: optional devex preflight helper, documentation and unit coverage.
Phase 2: CI status optimizer, lessons and resume validators behind opt-in flags.
Phase 3: independent QA, candidate archive, staged runtime validation.
Phase 4: governed skill publication or production deployment only with verified
destination, authorization, rollback and observed effect.

## Acceptance and metrics
Metrics require baseline measurement, not assumed improvements.
Target 30–50% fewer avoidable CI reruns, 40% fewer redundant provider status
calls, >=90% evidence completeness and zero unauthorized mutations.
All required checks must remain enforced. Trace every claim to evidence.

## Add-on candidates
Authenticated CI webhook receiver; external independent reviewer receipt;
performance/cost dashboard; HANDOFF schema validator; policy-drift detector;
cross-project CyberHIVE/CyberSKILLS compatibility tests. Each requires its
own security, value and ownership review before implementation.

## Stop conditions
Unknown skill provenance, lack of operator authority, unavailable reviewer,
failed tests, uncertain deployment state, secret exposure or source drift
must result in BLOCKED, not a release-complete claim.
