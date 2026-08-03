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
| MOP | Method of Procedure: schválený, auditovatelný plán provedení změny |

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


### EPIC-008 — Enterprise Change Governance and Method of Procedure

**Status:** Planned
**Goal:** Zavést enterprise change-control proces, ve kterém je každá významná
nebo produkční změna připravena jako schvalovaný, reprodukovatelný a
auditovatelný Method of Procedure dokument.

CyberCore bude podporovat kanonický `MOP` artefakt obsahující:

- identifikaci změny, vlastníka, zákazníka a dotčeného prostředí;
- obchodní a technický důvod změny;
- rozsah, výluky, závislosti a předpoklady;
- klasifikaci rizika, dopadu a očekávaného výpadku;
- maintenance window a komunikační plán;
- pre-checky a vstupní podmínky;
- přesný číslovaný postup provedení;
- hold points, abort conditions a rozhodovací body;
- rollback postup včetně podmínek jeho aktivace;
- post-checky, akceptační kritéria a důkazní materiál;
- kontakty, eskalační cestu a odpovědnosti;
- výsledný execution record a closeout report.

#### Approval chain

Minimální schvalovací model bude podporovat oddělené role:

1. **Preparer** — připraví MOP.
2. **Technical reviewer** — ověří technickou správnost.
3. **Requesting-side management approver** — schválí riziko, okno a obchodní
   dopad na straně provozovatele.
4. **Counterparty approver** — schválí provedení na straně zákazníka,
   partnera nebo jiné organizační jednotky.
5. **Execution operator** — provede přesně schválenou revizi MOP.
6. **Independent verifier** — ověří výsledek a uzavře změnu.

Schvalovací politika musí být konfigurovatelná podle rizika, prostředí,
zákazníka a typu změny.

#### Approval stamps and attestations

Každé schválení bude reprezentováno auditovatelným razítkem obsahujícím:

- identitu schvalující osoby nebo instance;
- organizační roli a stranu schválení;
- rozhodnutí: approve, reject, request changes nebo revoke;
- časové razítko;
- hash přesné revize MOP;
- komentář nebo podmínky schválení;
- původ schválení a použitý autentizační mechanismus.

Jakákoli změna obsahu po schválení automaticky zneplatní všechna razítka
navázaná na předchozí hash.

CyberCore musí podporovat také:

- schválení jinou nezávislou CyberCore instancí;
- federované nebo protistranné countersignature;
- kryptograficky ověřitelné attestation records;
- export schvalovacího balíčku do Markdown, JSON a PDF;
- dlouhodobě uchovatelný audit trail.

#### State machine

Základní stavový model:

```text
DRAFT
  -> TECHNICAL_REVIEW
  -> INTERNAL_APPROVAL
  -> COUNTERPARTY_APPROVAL
  -> SCHEDULED
  -> IN_PROGRESS
  -> VERIFICATION
  -> CLOSED

Alternative outcomes:
  -> CHANGES_REQUESTED
  -> REJECTED
  -> ABORTED
  -> ROLLED_BACK
```

Produkční provedení smí začít pouze proti přesnému hashi plně schválené revize.

#### Separation of duties

Výchozí enterprise politika:

- autor nesmí schválit vlastní MOP;
- execution operator nesmí být jediným verifierem;
- management approval nenahrazuje technical review;
- protistranné schválení nenahrazuje interní schválení;
- žádné schválení nesmí být přeneseno na změněnou revizi dokumentu;
- bypass vyžaduje explicitní emergency authority a samostatný auditní záznam.

#### Emergency changes

Nouzový režim bude podporovat zkrácený MOP, ale musí zachovat:

- identifikaci incidentu;
- explicitní emergency approval;
- známá rizika;
- bezpečný minimální postup;
- rollback nebo containment plán;
- evidenci provedených kroků;
- retrospektivní úplný MOP a management review po zásahu.

#### Planned work block

`WB-0028 — MOP Workflow and Approval Attestation v0.1`

První implementace má dodat:

- MOP Markdown a JSON Schema;
- validátor povinných sekcí;
- stavový automat;
- role a approval-policy model;
- hash-bound approval stamps;
- automatické zneplatnění approvalů po změně obsahu;
- interní a protistranné schválení;
- cross-instance countersignature contract;
- audit log;
- CLI příkazy `mop create`, `mop review`, `mop approve`, `mop execute`,
  `mop verify` a `mop close`;
- ukázkový enterprise change pack;
- testy separation-of-duties a approval invalidation.

Aktivace tohoto work blocku nesmí porušit pravidlo jednoho aktivního artefaktu
a proběhne až po uzavření aktuálních work blocků.

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
- Pull request: #32, ready for review; a corrective push requires fresh
  independent approval afterward.
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
- Activation-time snapshot: PR #32 head
  `c3868e058f42dfbb8c0c4bdf3eabfe094dd91ccf`, CI run `30784170890`,
  CodeQL run `30784170892`; all seven required contexts passed.
- Pre-correction snapshot: PR #32 head
  `034c77e156725169afb75e1cc89364bac252c67e`, CI run `30806185333`,
  CodeQL run `30806185411`; all seven required contexts passed.
- Merge-time evidence must be captured from the final PR head after the last
  push.
- Check-name distinction: `CodeQL` is informational; the required ruleset
  context is lowercase `codeql`.
- Rollback for one failed context preserves the active ruleset and every
  unaffected protection, changing only the broken required context through an
  explicitly approved settings operation.
- Complete ruleset disablement is reserved for ruleset-wide failure and
  requires equivalent replacement protection to be active first.

Next:

- Capture final-head CI and CodeQL evidence after the last corrective push.
- Update PR #32 metadata with the final head and hosted run IDs.
- Resolve both automated review threads.
- Obtain fresh independent approval from nulleimy after the final push.
- Merge only after all seven required checks succeed and approval is present.
- Verify protected main after merge and close WB-0026.

Critical flow:

```text
Reality -> Evidence -> Knowledge -> Confidence -> Decision
        -> Specification -> Implementation -> Verification -> Merge
