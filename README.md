# CyberCore

**AI-first infrastructure control plane for CyberDJS.**

CyberCore is the operational brain of the Eimy Herrer / CyberDJS ecosystem: a modular platform for infrastructure inventory, documentation, monitoring, security, deployment workflows, incident response and future self-healing automation.

The first provider target is **InterServer**: shared hosting, VPS, DirectAdmin, mail, DNS, WordPress, Nextcloud and selected Softaculous applications.

---

## Mission

Build a reproducible, secure, low-cost and open-source-ready platform for operating creative digital infrastructure.

CyberCore should help answer questions like:

- What services do we run?
- Where are they hosted?
- What changed recently?
- What is exposed to the internet?
- What needs an update?
- What is broken?
- What can be automated safely?
- What can be removed?
- What costs money and why?

---

## Product vision

CyberCore starts as an internal CyberDJS operations platform, but the architecture is designed so reusable framework logic can later be open-sourced.

```text
CyberCore
├── Core
├── Providers
│   ├── InterServer
│   ├── DirectAdmin
│   ├── GitHub
│   ├── Docker
│   ├── SSH
│   └── Future providers
├── Inventory
├── Documentation
├── Knowledge Graph
├── AI Operations
├── Deployment
├── Monitoring
├── Security
└── UI / CLI / TUI / MCP
```

---

## Current scope

```text
InterServer
├── Shared hosting
│   ├── eimyherrer.com
│   ├── mail
│   ├── WordPress
│   ├── Nextcloud
│   └── Softaculous apps on subdomains
└── VPS
    ├── DirectAdmin
    ├── system services
    └── future observability / automation stack
```

---

## Working tracks

CyberCore is managed in three parallel tracks:

| Track | Purpose |
|---|---|
| Delivery | Fix and improve real production services: Nextcloud, WordPress, mail, deployment, VPS. |
| Platform | Build reusable CyberCore capabilities: SDK, inventory, provider framework, docs generation. |
| Research | Explore AI, MCP, knowledge graphs and future-facing automation safely. |

Default capacity model: **70% Delivery / 20% Platform / 10% Research**.

---

## Operating principles

1. **Everything as Code** — infrastructure knowledge, docs, decisions and workflows live in Git.
2. **API before SSH** — prefer provider APIs for discovery and automation.
3. **Human-approved automation** — destructive actions require explicit approval.
4. **No secrets in Git** — credentials and private data never enter the repository.
5. **Low-cost by default** — every recurring cost must justify itself.
6. **Open-source ready** — separate reusable framework logic from private environment data.
7. **Documentation is a product** — docs must be useful, current and structured.
8. **Security by default** — design for least privilege, auditability and rollback.
9. **Remove before adding** — complexity is guilty until proven useful.
10. **AI assists, humans own** — AI can propose, explain and verify; humans remain accountable.

---

## Methodology

All work should be tracked as one of:

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

Structured contribution rules are defined in [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Immediate priorities

1. Revoke and rotate exposed InterServer secrets.
2. Build InterServer Provider v0.1.
3. Create machine-readable infrastructure inventory.
4. Generate sanitized documentation from inventory.
5. Audit and update Nextcloud using backup-first best practices.
6. Replace FTP-first deployment with a controlled Git-based workflow.

---

## Repository map

```text
README.md                     Project overview
roadmap.md                    Sprint and milestone tracking
VISION.md                     Long-term product vision
SECURITY.md                   Security rules and incident notes
CONTRIBUTING.md               Collaboration and request format rules
CHANGELOG.md                  Notable changes
LICENSE.md                    License decision placeholder

docs/
  architecture/               Architecture context and diagrams
  adr/                        Architecture Decision Records
  runbooks/                   Operational procedures
  meetings/                   Kickoffs and meeting notes
  manual-actions.md           Human-only action checklist
  risk-register.md            Known risks and mitigations

automation/
  scripts/                    Bootstrap and operational scripts
  ansible/                    Future configuration management
  docker/                     Future Compose/container assets
  terraform/                  Future infrastructure experiments

monitoring/                   Observability plans and configs
security/                     Hardening and audit notes
knowledge/                    Knowledge graph and generated docs
agents/                       AI-assisted operations agents
```

---

## Status

Project bootstrap started on **2026-07-08**.

Current phase: **Sprint 0 / Foundation Bootstrap**.

See [`roadmap.md`](roadmap.md) for sprint tracking and [`docs/manual-actions.md`](docs/manual-actions.md) for manual next steps.
