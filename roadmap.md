# CyberCore Roadmap

Project: **CyberDJS / CyberCore**  
Started: **2026-07-08**  
Updated: **2026-08-03**
Mode: living roadmap; GitHub `main` is the stable source of truth.

## Strategic outcome

Build an open, low-cost **Infrastructure Context & Intelligence Platform** that can:

- discover and explain infrastructure;
- preserve evidence, decisions, and operational context;
- verify and apply controlled changes;
- support monitoring, security, incident response, and cost optimization;
- evolve toward human-approved self-healing.

## Capacity baseline

- Jan: 4 MD/month.
- Eimy: 4 MD/month.
- Total: 8 MD/month.
- Recurring budget: <= 1000 CZK/month unless measurable value justifies more.

| Track | Allocation | Purpose |
|---|---:|---|
| Delivery | 70% | Keep production services healthy. |
| Platform | 20% | Build reusable CyberCore capabilities. |
| Research | 10% | Explore AI, knowledge graphs, and future automation safely. |

## Project language

| Prefix | Meaning |
|---|---|
| EPIC | Large capability or program increment |
| RFC | Proposal requiring discussion |
| ADR | Accepted architecture decision |
| KB | Knowledge Block: evidence and decision context |
| WB | Work Block: implementation and verification |
| BUG | Defect |
| SEC | Security item |
| OPS | Operational task |

## Program sequence

### EPIC-000 — Foundation

**Status:** Complete in v0.1.0 foundation release
**Goal:** Freeze identity, governance, architecture, engineering method, terminology, decision model, and knowledge model.

Delivered:

- Identity v1.0.
- Governance, manifesto, glossary, and design-system foundation.
- Public Framework + Private Overlay.
- Foundation layer.
- `ARCHITECTURE.md`.
- CXP v1 design contracts.
- WB-0006 Exchange Runtime Design Freeze.

Exit criteria:

- [x] Foundation documents complete.
- [x] CXP package, runtime, publisher, and Git integration specified.
- [x] README and changelog aligned.
- [x] Runtime alpha promoted to foundation baseline.
- [x] Public-release license and readiness gate completed.
- [x] Release branding assets added.

### EPIC-001 — Runtime

**Status:** Foundation baseline shipped; next iteration planned
**Goal:** Implement the minimal safe CyberCore runtime according to CXP v1.

Planned capabilities:

- unified `cybercore` CLI;
- `doctor`, `status`, `sync`, `verify`, `apply`;
- repository identity validation;
- transport adapter boundary;
- deterministic state machine;
- explicit human approval gate;
- structured result and failure reporting;
- rollback contract where supported.

First milestone:

- first end-to-end Work Block:
  `publish -> transport -> verify -> READY -> apply -> test -> commit -> push -> PR`.

### EPIC-002 — Provider Framework

**Status:** Draft implementation exists in PR #5; review after Runtime baseline  
**Goal:** Provide normalized adapters without leaking vendor-specific behavior into the core.

Initial providers:

- InterServer API;
- DirectAdmin;
- read-only SSH diagnostics;
- GitHub.

### EPIC-003 — Infrastructure Inventory and Knowledge

**Status:** Planned  
**Goal:** Convert infrastructure observations into machine-readable inventory and reusable knowledge.

Initial scope:

- domain and DNS;
- mailboxes, aliases, and routing;
- shared hosting and Softaculous applications;
- VPS operating system, services, ports, firewall, and storage;
- WordPress and Nextcloud topology;
- provenance, confidence, and risk metadata.

### EPIC-004 — Nextcloud Reliability

**Status:** Planned; original operational priority  
**Goal:** Upgrade and stabilize Nextcloud using backup-first, audit-first practices.

Includes:

- PHP compatibility;
- database and application upgrade path;
- Redis/APCu configuration;
- cron and background jobs;
- HSTS and reverse-proxy headers;
- storage paths and permissions;
- security and performance warnings;
- tested rollback.

### EPIC-005 — Deployment Baseline

**Status:** Planned  
**Goal:** Replace FTP-first changes with controlled Git-based deployment.

Includes:

- staging-lite strategy;
- backup-before-change;
- deployment verification;
- release notes;
- rollback procedure;
- low-risk pilot.

### EPIC-006 — Monitoring, Security, and Backups

**Status:** Planned  
**Goal:** Establish measurable operational health.

Includes:

- uptime, SSL, mail, disk, WordPress, and Nextcloud checks;
- RPO, RTO, retention, and restore tests;
- SSH and DirectAdmin hardening;
- SPF, DKIM, and DMARC;
- dependency and plugin audit;
- secrets policy and rotation workflow.

### EPIC-007 — Intelligence and Controlled Self-Healing

**Status:** Planned  
**Goal:** Turn observations and knowledge into explainable recommendations and safe remediation.

Includes:

- knowledge graph;
- drift and risk analysis;
- incident-response drafts;
- cost optimization;
- monthly health reports;
- non-destructive remediation recommendations;
- approved remediation playbooks.

## Immediate security actions

These remain operational blockers and must not disappear inside platform work:

- [ ] Revoke the exposed InterServer API key.
- [ ] Rotate the exposed InterServer 2FA/TOTP secret.
- [ ] Store replacement secrets outside chat and Git.
- [ ] Produce the first sanitized infrastructure snapshot.
- [ ] Record the production/development separation strategy.

## Working rule

No new implementation epic starts before its required foundation or specification change is merged into `main`.

## Current Platform Checkpoint

WB-0025 security verification is merged through PR #31. Hosted GitHub Actions CI
run `30774683751` and hosted CodeQL run `30774683774` passed. GitHub CodeQL
Default setup conflicted with the checked-in Advanced setup, was disabled by
explicit human action, and the retry succeeded.

WB-0026 remains active for documentation, review, merge, and post-merge
verification of `main` branch protection. Main protection was explicitly
approved by a human, activated, and verified for PR #32, but WB-0026 must not
be closed until PR #32 is independently approved, merged, and protected `main`
is verified after merge.

Active protection evidence:

- Repository: `cyberDJs/CyberCore`.
- Pull request: #32, still draft.
- Ruleset: `18986451`, `main-branch-protection`, target `branch`, target ref
  `~DEFAULT_BRANCH`, enforcement `active`, bypass actors `none`,
  `current_user_can_bypass: never`.
- Activated: `2026-08-03T10:47:03.259+02:00`.
- Rules: deletion and non-fast-forward protection enabled; pull request
  required; one approving review required; stale approvals dismissed after
  push; review thread resolution required; CODEOWNERS review not required;
  last-push approval not required; linear history not required.
- Allowed merge methods: merge, squash, rebase.
- Required checks: `tests (python 3.11)`, `tests (python 3.12)`,
  `tests (python 3.13)`, `tests (python 3.14)`, `quality`, `package`, `codeql`.
- Required status-check policy: `strict_required_status_checks_policy: true`;
  `do_not_enforce_on_create: false`.
- Verification against PR #32 head
  `c3868e058f42dfbb8c0c4bdf3eabfe094dd91ccf`: CI run `30784170890` passed,
  CodeQL run `30784170892` passed, all seven required contexts passed,
  `mergeable: MERGEABLE`, merge state `BLOCKED`, review decision
  `REVIEW_REQUIRED`, and PR remains draft.
- Check-name distinction: `CodeQL` is informational; the required ruleset
  context is lowercase `codeql`.
- Rollback: disable enforcement only for ruleset `18986451`, verify no active
  `main` enforcement remains, repair on a feature branch, and reactivate only
  after hosted checks succeed.

Next:

- Update PR #32 metadata to reflect active and verified main protection.
- Mark PR #32 ready for review.
- Request independent approval from nulleimy.
- Merge only after all seven required checks succeed and approval is present.
- Verify protected main after merge and close WB-0026.

Critical flow:

```text
Reality -> Evidence -> Knowledge -> Confidence -> Decision
        -> Specification -> Implementation -> Verification -> Merge
