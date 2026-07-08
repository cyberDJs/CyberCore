# CyberCore Roadmap

Project: **CyberDJS / CyberCore**  
Started: **2026-07-08**  
Mode: living roadmap, updated continuously.

---

## Strategic targets

- Fully automated InterServer infrastructure management.
- Self-healing hosting with human-approved remediation first.
- Monitoring and observability.
- Security hardening.
- Asset management.
- Knowledge base and knowledge graph.
- Cost optimization.
- Open-source-ready framework.

---

## Capacity baseline

- Jan: 4 MD/month.
- Eimy: 4 MD/month.
- Total: 8 MD/month.
- Budget: <= 1000 CZK/month unless a higher cost has measurable return.

Default allocation:

| Track | Allocation | Purpose |
|---|---:|---|
| Delivery | 70% | Keep real production services healthy: Nextcloud, WordPress, mail, VPS, deployment. |
| Platform | 20% | Build CyberCore reusable platform capabilities. |
| Research | 10% | Explore AI, MCP, knowledge graphs and future-facing automation safely. |

---

## Project language

| Prefix | Meaning |
|---|---|
| ADR | Architecture Decision Record |
| EPIC | Large initiative |
| SPR | Sprint |
| TASK | Concrete task |
| BUG | Defect |
| SEC | Security item |
| RFC | Proposal for discussion |
| OPS | Operational task |

---

## Active epics

### EPIC-001 — Provider Framework

**Status:** Approved  
**Track:** Platform  
**Goal:** Build a reusable provider framework where InterServer is Provider #1, not a hardcoded exception.

Planned capabilities:

- Provider interface.
- InterServer provider.
- DirectAdmin provider.
- GitHub provider.
- SSH provider for diagnostics.
- Inventory export.
- Health metadata.
- Documentation generation hooks.

### EPIC-002 — Knowledge Engine

**Status:** Approved  
**Track:** Platform / Research  
**Goal:** Convert infrastructure inventory into structured knowledge: docs, graphs, runbooks and AI context.

### EPIC-003 — Deployment Engine

**Status:** Approved  
**Track:** Delivery / Platform  
**Goal:** Replace FTP-first deployment with controlled Git-based deployment, verification and rollback.

### EPIC-004 — Nextcloud Reliability

**Status:** Approved  
**Track:** Delivery  
**Goal:** Update and stabilize Nextcloud using backup-first, audit-first best practices.

### EPIC-005 — Security and Secrets Hygiene

**Status:** Approved  
**Track:** Delivery / Security  
**Goal:** Establish safe handling of API keys, 2FA, SSH keys, tokens and private infrastructure data.

---

## Sprint 0 — Foundation Bootstrap

**Timestamp:** 2026-07-08 12:40 CEST  
**Updated:** 2026-07-08 17:35 CEST  
**Status:** In progress  
**Owner:** Jan + Eimy + AI project team  
**Scope:** Repository, initial documentation, secrets hygiene, first inventory, methodology.

### Goals

- [x] Create GitHub repository: `cyberDJs/CyberCore`
- [x] Confirm repository access exists
- [x] Create initial project files
- [x] Create manual actions list
- [x] Define source-of-truth structure
- [x] Add structured contribution request policy
- [x] Add project tracks: Delivery / Platform / Research
- [x] Confirm InterServer API is reachable
- [x] Download InterServer OpenAPI specification locally
- [ ] Revoke exposed InterServer API key
- [ ] Rotate exposed InterServer 2FA/TOTP secret
- [ ] Create new InterServer API key and store it outside chat/Git
- [ ] Prepare first sanitized infrastructure snapshot
- [ ] Decide production/development separation strategy

### Notes

The current production web is also used as development. This is accepted temporarily due to cost/time limits, but the roadmap must move toward separation using the lowest-cost viable model.

A sensitive InterServer API response was pasted into chat during API smoke testing. Treat exposed API key history and 2FA seed as compromised and rotate.

---

## Sprint 1 — Inventory and Architecture

**Target window:** July 2026  
**Status:** Planned

### Goals

- [ ] Implement InterServer Provider v0.1
- [ ] Export InterServer service inventory
- [ ] Export DirectAdmin account inventory
- [ ] Map DNS records for `eimyherrer.com`
- [ ] Map mailboxes, aliases and routing
- [ ] Map WordPress installation
- [ ] Map Nextcloud installation
- [ ] Map Softaculous apps and classify: keep / evaluate / remove
- [ ] Map VPS OS, services, ports, firewall and storage
- [ ] Create first architecture diagram
- [ ] Update risk register from real inventory

### Deliverables

- `cybercore inventory interserver`
- sanitized inventory JSON
- generated inventory Markdown
- initial Mermaid architecture diagram

---

## Sprint 2 — Deployment Baseline

**Target window:** August 2026  
**Status:** Planned

### Goals

- [ ] Move away from FTP-first deployment
- [ ] Select deployment model: Git pull, GitHub Actions, rsync, or hybrid
- [ ] Define staging-lite strategy
- [ ] Define backup-before-deploy procedure
- [ ] Create rollback procedure
- [ ] Create release notes template
- [ ] Pilot deployment workflow on low-risk target

---

## Sprint 3 — Monitoring and Backups

**Target window:** September 2026  
**Status:** Planned

### Goals

- [ ] Define uptime checks
- [ ] Define SSL expiration checks
- [ ] Define mail health checks
- [ ] Define disk/storage checks
- [ ] Define WordPress/Nextcloud checks
- [ ] Define backup policy: RPO, RTO, retention
- [ ] Run first restore test

---

## Sprint 4 — Security Hardening

**Target window:** October 2026  
**Status:** Planned

### Goals

- [ ] Secrets policy
- [ ] SSH baseline
- [ ] DirectAdmin hardening review
- [ ] WordPress hardening review
- [ ] Nextcloud hardening review
- [ ] Mail hardening: SPF, DKIM, DMARC
- [ ] Dependency and plugin audit
- [ ] Public/private repository split strategy

---

## Sprint 5 — AI Documentation and Knowledge Graph

**Target window:** November 2026  
**Status:** Planned

### Goals

- [ ] Build machine-readable inventory
- [ ] Generate documentation from inventory
- [ ] Create knowledge graph model
- [ ] Create AI chat interface over project docs
- [ ] Add architecture decision records
- [ ] Add monthly AI-generated infrastructure report draft

---

## Sprint 6 — Controlled Self-Healing

**Target window:** December 2026  
**Status:** Planned

### Goals

- [ ] Define safe remediation playbooks
- [ ] Add incident response templates
- [ ] Add cost optimization review
- [ ] Add monthly platform health report
- [ ] Prepare open-source sanitization strategy
- [ ] Implement first non-destructive self-healing recommendation workflow
