# Operator reporting — material-event checkpoint adapter (candidate)

**Status:** isolated review candidate. **Authority:** no new runtime permission, scheduler, provider connector, live transport, database or production deployment.

## User outcome

The operator should receive one concise Czech status report when an already-verified material change occurs, not repeated copies of the same event during later polls. The next-step/impact fields in `operator_reporting` remain the user-facing contract.

## Scope and API

`checkpoint_operator_update(update, last_delivered_fingerprint=None)` accepts a **caller-supplied, already-authenticated and sanitized** `OperatorUpdate` and a 64-character SHA-256 fingerprint of the last *successfully delivered* report. It returns `CheckpointDecision(report, fingerprint, reason)`:

- `MATERIAL_CHANGE`: text plus SHA-256; caller may deliver report.
- `UNCHANGED`: no text and same fingerprint; suppress duplicate.
- `NON_MATERIAL`: no text and no replacement checkpoint.
- malformed event, evidence URL, status, SHA, approval flag, changed flag or previous fingerprint: fail closed (`ValueError`).

The fingerprint is an identity of the rendered text **not** an authenticated security receipt. This module does not fetch GitHub, send to Slack/Zulip/ChatGPT, authenticate provider data, persist state, grant permissions, or call a model. A sha256 digest is not a durable event ledger or a privacy guarantee. Avoid secret-bearing content before calling this module; it is *not* a secret scanner.

## Required external integration gates (future, separately approved)

1. Acquire complete authenticated evidence (repository, PR, exact HEAD/base, workflow runs and review provenance); fail closed if origin/pagination is uncertain. Existing GitHub connector fetch_commit_workflow_runs is PR-event-only and cannot prove main-push PASS.
2. Redact sensitive text *before* creating `OperatorUpdate`; never read credential-bearing sources through A0.
3. Store **last successfully delivered** fingerprint in a governed durable store with an atomic compare-and-set or single-writer lease. Do not advance checkpoint before transport delivery acknowledgment.
4. On concurrent writers or changed HEAD/base, stop and require `REPLAN_REQUIRED`; no stale approval reuse.
5. Send only material events via an independently approved transport; rate-limit and audit consent. The existing hourly ChatGPT monitor is already a separate scheduler.
6. Observe delivery failures, replay and retries; do not infer that a returned fingerprint proves delivery.
7. Maintain A3/A4 human approval boundaries, including merge, staging writes, production and secret access.

## Acceptance / safety tests

- identical material text with previously delivered digest is suppressed;
- change to impact produces a new fingerprint;
- non-material messages do not advance checkpoint;
- invalid/missing evidence and malformed checkpoint/flags fail closed;
- Python 3.11–3.14, Ruff, Pyright, CodeQL and pinned real CyberHIVE unchanged; independent review required.

## Rollback and impact

No production execution path calls this adapter. Rollback: do not import it or close the Draft PR. No external state migration. Operational behavior remains unchanged until an independently authorized, fully verified collector/transport integration exists.
