# CyberCore operator CI snapshot → report boundary (candidate)

**Status:** isolated Draft PR; no live GitHub collector, scheduler, delivery pipeline, database, production change or additional authority.

## Why

The existing `caser41_github_snapshot.reconcile_github_snapshot` verifies only **structural** consistency of externally acquired workflow/job records. It returns `CONSISTENT_ONLY / PROVIDER_ORIGIN_AND_PAGINATION_UNVERIFIED` even if all mandatory jobs appear successful. This is deliberately not a verified CI attestation. Separately, `operator_reporting` and `operator_checkpoint` render and deduplicate sanitized events, but must not invent a PASS.

The pure `ci_snapshot_operator_update` adapter receives the PR number, expected SHA, observed provider HEAD, workflow records and job records **in the same call** and invokes `reconcile_github_snapshot` internally. It deliberately rejects a detached/reusable `Reconciliation` result, so an old verdict cannot be silently relabeled with a fresh expected SHA. The caller must still acquire *authentic records for the specified PR* and verify current HEAD before/after acquisition; a caller can lie about PR identity, so this is **not proof of provenance**. The adapter bridges the interfaces without promoting unverified provider input:

- `CONSISTENT_ONLY` becomes **UNKNOWN / critical_evidence_missing**, with plain-language user impact and action to verify provider origin, complete pagination, current HEAD;
- known `BLOCKED` reconciliation codes become **BLOCKED / checks_failed** (or `source_drift` for HEAD_DRIFT);
- unsupported state/reason, malformed PR number/SHA or non-boolean `changed`: **raise ValueError**;
- output is fixed, nonsecret Czech text, never echoes an arbitrary provider-supplied message.

The result can be passed to `format_operator_update` and `checkpoint_operator_update` as a material event **candidate**. It is not proof that the underlying GitHub data are authentic.

## Required evidence and release gates

An actual verified GitHub adapter would have to bind repository and PR identity through an authenticated source, read HEAD/base before and after acquisition, enumerate complete workflow job pagination and run attempts, authenticate provider identity and verify protections/reviews. This version checks that the supplied expected HEAD and observed provider HEAD agree *within the reconciliation call*, but it cannot attest that supplied workflows/jobs belong to the claimed PR. The existing connector reports PR-triggered workflow runs only; **main-push CI is UNKNOWN without an independently observed main-push check**. A source-visible PASS is never inferred from structural-only data.

No A3/A4 action can be authorized by this status adapter; merge/deploy require their separate review and scoped approval. The caller must redact sensitive inputs *before* using the reporting/checkpoint libraries, and persist last-delivered fingerprint only after confirmed transport ACK under a governed single-writer/CAS store. This candidate does not add that store or transport.

## Validation, effect and rollback

Unit tests exercise structural-only UNKNOWN, known BLOCKED reasons, drift, malformed shapes, rejection of detached cached verdicts, deduplication and distinct PR identity. Existing full CI matrix, CodeQL and real pinned CyberHIVE contract must pass on exact HEAD; obtain independent code/security review before any merge.

**User effect now:** none in live notifications; library-only integration improves correctness of future status reports. **Rollback:** do not import module / close Draft PR, preserving evidence. No existing runtime entrypoint or production configuration changed.
