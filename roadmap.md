# CyberCore Roadmap

Project: **CyberDJS / CyberCore**  
Started: **2026-07-08**  
Mode: living roadmap, updated continuously.

## Strategic targets

- Fully automated InterServer infrastructure management.
- Self-healing hosting.
- Monitoring and observability.
- Security hardening.
- Asset management.
- Knowledge base.
- Cost optimization.
- Open-source-ready framework.

## Capacity baseline

- Jan: 4 MD/month.
- Eimy: 4 MD/month.
- Total: 8 MD/month.
- Budget: <= 1000 CZK/month unless a higher cost has measurable return.

---

## Sprint 0 — Foundation Bootstrap

**Timestamp:** 2026-07-08 12:40 CEST  
**Status:** In progress  
**Owner:** Jan + AI project team  
**Scope:** Repository, initial documentation, secrets hygiene, first inventory.

### Goals

- [x] Create GitHub repository: `cyberDJs/CyberCore`
- [x] Confirm repository access exists
- [ ] Revoke leaked InterServer API key
- [ ] Create new InterServer API key and store it outside chat/Git
- [ ] Create initial project files
- [ ] Create manual actions list
- [ ] Define source-of-truth structure
- [ ] Collect InterServer/DirectAdmin inventory
- [ ] Prepare first infrastructure snapshot
- [ ] Decide production/development separation strategy

### Notes

The current production web is also used as development. This is accepted temporarily due to cost/time limits, but the roadmap must move toward separation using the lowest-cost viable model.

---

## Sprint 1 — Inventory and Architecture

**Target window:** July 2026  
**Status:** Planned

### Goals

- [ ] Export InterServer service inventory
- [ ] Export DirectAdmin account inventory
- [ ] Map DNS records for `eimyherrer.com`
- [ ] Map mailboxes, aliases and routing
- [ ] Map WordPress installation
- [ ] Map Nextcloud installation
- [ ] Map Softaculous apps and classify: keep / evaluate / remove
- [ ] Map VPS OS, services, ports, firewall and storage
- [ ] Create first architecture diagram
- [ ] Create first risk register

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
