# OPS-0001 — Security and Source-of-Truth Baseline

Status: Active candidate
Activated by: CASER / CASER-SOURCER audit kickoff
Date: 2026-08-17
Canonical repository: `cyberDJs/CyberCore`
Target branch: `docs/state-reconcile-security-baseline`

## Goal

Establish the next safe operational baseline before any production-changing CyberCore automation continues.

The immediate objective is to reconcile current source-of-truth state and turn unresolved security blockers into evidence-backed, human-approved operational steps.

## Source-of-truth model

- GitHub `main` remains the canonical product state for CyberCore code, documentation, schemas, and governance.
- Google Drive `CyberCore/CASER-E` is the evidence, archive, and collaboration layer.
- CASER-M, if materialized later, is a mirror of declared canonical sources, not an independent authority.
- Historical screenshots, Drive copies, pasted chat exports, and old working folders are evidence until reconciled.

## Evidence basis

This work is opened because current canonical planning still lists unresolved immediate security actions:

- revoke the exposed InterServer API key;
- rotate the exposed InterServer 2FA/TOTP secret;
- store replacement secrets outside chat and Git;
- produce the first sanitized infrastructure snapshot;
- record the production/development separation strategy.

Google Drive also contains earlier runbook/checklist evidence for the InterServer API-key revocation path.

## Scope

### In scope

- Read-only reconciliation of GitHub, Google Drive, and available CASER-E evidence.
- Classification of current evidence into authoritative state, historical evidence, stale material, and open blockers.
- Safe documentation of the next operational sequence.
- Drafting MOP/runbook material for secret rotation, sanitized inventory, and restore-first infrastructure baseline.
- Preparing non-production PRs and documents.

### Out of scope without explicit human approval

- Revoking or creating InterServer credentials.
- Handling or storing plaintext secrets.
- SSH access to production systems.
- Production configuration changes.
- DirectAdmin, VPS, mail, DNS, WordPress, Nextcloud, or billing mutations.
- Accepting ADRs or policy exceptions.

## Required outputs

1. Source-of-truth map for CyberCore project state.
2. Evidence inventory for unresolved security blockers.
3. Sanitized infrastructure snapshot plan.
4. Secret-rotation MOP draft with no secret values.
5. Production/development separation note.
6. Recommendation for the next implementation work block after blockers are resolved or explicitly deferred.

## Safety rules

- Do not store API keys, TOTP seeds, passwords, SSH private keys, cookies, or recovery codes in GitHub, Google Drive, Slack, or chat.
- Store only safe references, aliases, providers, timestamps, scopes, and verification status.
- Treat missing provenance as `UNKNOWN`.
- Treat old Drive copies as historical unless they match canonical GitHub state.
- Do not promote an idea, checklist, or chat message to current truth without authority evidence.

## Initial decision

The planned MOP Workflow and Approval Attestation work remains important, but this operational baseline takes precedence because unresolved credential exposure and missing sanitized inventory are safety blockers.

## Exit criteria

- No unresolved source-of-truth ambiguity for current project state.
- Security blockers are either verified closed or represented by approved MOPs with owner, status, and evidence requirements.
- CASER-E has a clear evidence/archive structure for this project.
- Next work block can begin without hiding active security debt.
