# CyberCore Roadmap

Project: **CyberDJS / CyberCore**  
Started: **2026-07-08**  
Updated: **2026-09-04**
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
- rollback contract where supported;
- governed human interface through Cyber Voice.

First milestone:

- first end-to-end Work Block:
  `publish -> transport -> verify -> READY -> apply -> test -> commit -> push -> PR`.

#### WB-0036 — Cyber Voice Foundation

**Status:** implementation proposed for review

Foundation scope:

- vendor-neutral `Utterance -> Intent -> ActionRequest` contracts;
- conversational session state with interruption and cancellation;
- fail-closed HOWEDO continuity adapter boundary;
- fail-closed OATHDO governance adapter boundary;
- canonical CyberCore approval verification for mutation readiness;
- voice approval intent capture that cannot self-authorize execution;
- audit-friendly voice lifecycle events;
- architecture and ADR documentation;
- no microphone, STT, TTS, speaker authentication, direct execution, deployment, or production mutation.

Next Voice work after Foundation review:

1. streaming audio adapter contract and barge-in transport;
2. provider-neutral STT/TTS adapters;
3. model-backed multilingual intent compiler with regression evaluation;
4. CASEBOOK/CASER session and evidence persistence;
5. bounded tool routers for terminal, GitHub, Slack, Drive, browser, and infrastructure;
6. speaker-identity design only after a dedicated security review.

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

WB-0025 security verification is merged through PR #31 and remains verified.

WB-0026 Main Branch Protection Enforcement was independently approved and
merged through PR #32.

Completion evidence:

- Final PR head:
  `bb14c930dd4404c665dc8faec8a3cd89ce812df4`.
- Merge commit:
  `00b408dd9439caa7e6c660737d1123d0eaa1c12f`.
- CI run `30827098051`: passed.
- CodeQL run `30827098042`: passed.
- Independent approval: `nulleimy`.
- Automated review threads were resolved before merge.
- Ruleset `18986451`, `main-branch-protection`, was last verified active
  before merge, with no bypass actors and seven required status contexts.
- This closeout does not claim a separate post-merge repository-settings read.

Current protection recovery evidence (2026-09-04):

- Live preflight against `main@14d4c6c4beb6b03aaedfaf2a76a521a038c98cb1`
  observed `rulesets=[]` and `main` not protected.
- The original ruleset `18986451` remains historical evidence only; it is not
  a current live settings identifier.
- After explicit repository-settings approval, equivalent protection was
  restored as ruleset `22291749` (`main-branch-protection`).
- Post-restore verification observed enforcement `active`, no bypass actors,
  `current_user_can_bypass: never`, all seven required status contexts,
  strict required status checks, and `main` reporting `protected=true`.
- The cause and deletion provenance of the missing historical ruleset remain
  unknown; no actor or cause is inferred without audit evidence.
- Detailed evidence:
  `docs/evidence/2026-09-04-main-protection-restore.md`.

Historical successor status:

- WB-0026 was closed by its post-merge transition.
- WB-0027 — Visual Documentation and Learn Capture v0.1 was subsequently
  independently approved and squash-merged through PR #34 as
  `94cb1998274e31e9ce3314f59d2e0ae290bc40cc`.
- The former instructions to review the WB-0026 closeout, create the WB-0027
  implementation branch, and propose WB-0027 are retired and must not be used
  as current operator actions.
- Current work selection must resolve live `main` and the current canonical
  project-state artifacts before any implementation or merge decision.

Critical flow:

```text
Reality -> Evidence -> Knowledge -> Confidence -> Decision
        -> Specification -> Implementation -> Verification -> Merge
```
