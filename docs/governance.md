# CyberCore Governance

Status: Accepted

## Decision layers

### Constitutional

Includes identity, philosophy, principles, constitution and terminology.

Changes require:

- unanimous approval from Jan and Eimy,
- an ADR,
- explicit rationale and impact.

### Architectural

Includes provider APIs, repository structure, core abstractions, SDK and public interfaces.

Changes require:

- ADR,
- review,
- approval from at least two maintainers.

### Operational

Includes bug fixes, tests, runbooks, provider updates, monitoring changes and ordinary documentation.

Operational changes should remain lightweight and reviewable.

## ADR policy

An ADR is required for:

- architecture,
- public APIs,
- structural changes,
- long-lived project principles.

An ADR is not required for every commit.

## Experiment policy

Experiments are allowed only when isolated from production architecture and clearly marked experimental.

## Community contributions

Community contributions are welcome after maintainer review.

## AI autonomy

AI may act without per-action approval only when the action is:

- safe,
- reversible,
- covered by an approved runbook,
- auditable,
- limited in scope.

Otherwise human approval is mandatory.

## Non-negotiable rule

> No silent structural changes.

No one may knowingly change the agreed workflow, repository structure or system skeleton without review, notice and a recorded rationale.

## Project integrity rules

- Integrity over popularity.
- No hidden decisions.
- Merge only what is understood.
