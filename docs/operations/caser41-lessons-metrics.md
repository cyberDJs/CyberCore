# CASER v4.1: Lessons & Metrics candidate

Status: isolated / opt-in. Program issue #136. This adds deterministic
evaluation helpers, **not** a lesson database, telemetry collector, deployed
scheduler, production policy engine or self-editing CASER skill.

## Operational lesson review

`caser41_lessons.assess_lesson` checks nonempty identity/context/root-cause/
guardrail, evidence references, bounded confidence, timezone-aware verification
and expiry dates, contradictory evidence, project and context changes.
All timestamp comparisons are normalized to UTC instants to avoid the
repeated-hour DST `fold` ambiguity (not local wall-clock ordering).
It returns `ELIGIBLE_FOR_REVIEW`, `REVALIDATION_REQUIRED` or `REJECTED`.

`ELIGIBLE_FOR_REVIEW` means a reviewer may compare against fresh primary
sources; it does not establish root-cause truth, authenticate evidence or
authorize an action. No lesson may override current source-of-truth, security
policy, permissions, approvals or independent verification. Persisting lesson
records and linking them to source evidence requires a separately reviewed
trusted adapter, including retention and tamper controls.

Concrete prevention candidate: repeated Ruff-format CI failures in PR
#137 / #139 should suggest a pre-commit formatter check. That is a
**proposal** based on observed failures, not an automatic policy change.

## Run metrics

`caser41_metrics.aggregate_run_metrics` reports total outcomes, verified,
blocked, failed, rolled back, time-to-verified (when all VERIFIED run durations
are present), aggregate CI retries and provider status polls (only when the
entire sample has these measurements). Missing observations remain `None`,
never zero, and records with duplicate IDs/invalid counters are rejected.
The caller must provide authenticated, nonduplicated completed run events.
No actual baseline is claimed by this module.

Do not infer speedup from these aggregates alone. Before/after comparisons
must control for run difficulty, sample size, time horizon and workflow
configuration. Report raw numerators, denominators, exclusions and provenance.
Do not collect secrets, prompts, personal content or full logs as metrics.

## Evaluation and rollback

Tests cover stale/context-switched/contradictory lessons, missing evidence,
malformed shapes, outcomes including failures, unknown telemetry, nonfinite
durations and duplicate IDs. These are pure, side-effect-free functions;
deactivation simply stops importing them.

Follow-ups: design trusted versioned lesson persistence and receipt provenance,
status event ingestion, metrics baseline measurement, dashboards, staged CASER
v4.1 release and independent verifier signoff. No deployment authorized by
these utilities.
