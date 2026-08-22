# CyberCore Project State

_Last updated: 2026-08-22 14:16 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `wb-0033-interserver-isolated-staging-target`
- Active pull request: #54 — WB-0033 isolated InterServer staging target
- Active artifact: `WB-0033 — InterServer Isolated Staging Target`
- Active work block: `WB-0033 — InterServer Isolated Staging Target`
- Last verified `main`: `70346d63ba2b17df17085797e963bb9dbd692282`
- Governance rule: provider mutation, secret mutation, staging-apply, and production mutation authority remains reserved to explicit Jan Kočí authorization
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

PR #53 completed the authorized WB-0032 Phase B read-only InterServer discovery preparation and was squash-merged into canonical `main` as `70346d63ba2b17df17085797e963bb9dbd692282`.

The subsequent WB-0033 slice moved from read-only discovery to a separately authorized, tightly bounded provider mutation required to establish an isolated staging target. The operator separately authorized creation of the DirectAdmin staging subdomain, one Cloudflare DNS-only A record, a dedicated Cloudflare ACME token stored in DirectAdmin, one manual wildcard renewal, a read-only production document-root metadata check, and standing unattended renewal authority for the existing `eimyherrer.com` + `*.eimyherrer.com` certificate through the existing DirectAdmin -> Cloudflare integration.

PR #54 records the resulting verified runtime evidence and canonical-state reconciliation. The operator has explicitly authorized finalization and squash merge of PR #54, but merge remains fail-closed until the current exact head passes CI, CodeQL, and fresh Codex review with no unresolved valid finding.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. treat merged WB-0030, WB-0031, and PR #53/WB-0032 Phase B preparation as the canonical fail-closed readiness/discovery foundation;
3. establish WB-0033 as the verified runtime identity for the isolated InterServer staging target;
4. preserve Cloudflare as authoritative DNS and DirectAdmin as hosting/SSL control plane without introducing a second public DNS source of truth;
5. preserve the verified staging/production document-root non-overlap without reading production application content;
6. preserve the bounded DirectAdmin -> Cloudflare DNS-01 -> Let's Encrypt wildcard renewal path and the operator's standing authority only for unattended renewal of the existing wildcard certificate;
7. keep `staging_apply` / application deployment blocked until a later work block receives fresh explicit remote-write authorization;
8. keep production application write authority false;
9. keep secret values out of GitHub, Drive, chat, Slack, CASER documents, and ordinary evidence;
10. complete PR #54 exact-head gates and execute only the already-authorized squash merge if all gates remain green.

## Current status

- Work block: `WB-0033` verified; PR #54 finalization/merge gate active
- Branch: `wb-0033-interserver-isolated-staging-target`
- Pull request: #54
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- ADR-0006 lifecycle status: Accepted
- ADR-0006 decision date: 2026-08-20
- ADR-0006 authority: Jan Kočí
- ADR-0006 decision state: `DECIDED`
- WB-0029 / PR #47: merged as `09750d7c5b2e49b9b4006c1288391d6d5c6066d5`
- PR #48 post-merge reconciliation: merged as `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- WB-0030 / PR #49: merged as `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- PR #50 post-merge reconciliation / WB-0031 kickoff: merged as `4a1374cbef7d142f8386ea7774208effc05d54ec`
- WB-0031 / PR #51: merged as `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- WB-0032 definition/kickoff / PR #52: merged as `304f4234e4f52c2375d904b45d1ed0c4fe31511c`
- WB-0032 Phase B preflight / PR #53: merged as `70346d63ba2b17df17085797e963bb9dbd692282`
- InterServer shared-hosting service identity: VERIFIED, `website_id=1439764`, primary hostname `eimyherrer.com`
- DirectAdmin control plane: VERIFIED
- Staging hostname: VERIFIED, `staging.eimyherrer.com`
- Staging document root: VERIFIED, `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- Production document-root metadata: VERIFIED by separately authorized read-only metadata call, `/home/eimyherr/domains/eimyherrer.com/public_html`
- Normalized path overlap: `same_path=false`, `staging_inside_production=false`, `production_inside_staging=false`
- Production application content read: false
- Cloudflare authoritative DNS: VERIFIED
- Staging DNS record: VERIFIED, `A staging.eimyherrer.com -> 162.250.126.107`, DNS only / `proxied=false`
- Staging HTTP: VERIFIED, HTTP 200 from InterServer origin
- Staging HTTPS/TLS: VERIFIED, HTTP 200 with TLS verification success
- DirectAdmin Cloudflare ACME provider: VERIFIED configured
- Dedicated Cloudflare ACME token: stored in DirectAdmin; secret value not recorded in ordinary evidence
- Manual wildcard renewal: VERIFIED end-to-end through DirectAdmin + Cloudflare DNS-01 + Let's Encrypt
- Wildcard SANs: `eimyherrer.com`, `*.eimyherrer.com`
- Current wildcard validity: through 2026-11-20
- Standing unattended ACME renewal authority: explicitly granted for that same wildcard certificate through the existing integration only
- Bounded provider/DNS mutations occurred under separate explicit approvals; unrelated DNS/mail/billing/VPS/application changes did not occur
- New paid hosting service ordered: false
- Application deployed to staging: false
- Staging application remote write allowed: false
- Production application write allowed: false
- Secret values stored in ordinary evidence: none
- PR #54 squash merge authority: explicitly granted by the operator on 2026-08-22
- GitHub `main`: canonical product state
- Google Drive CASER-E: evidence/archive/collaboration layer only, not canonical product state

## Secret-handling boundary

Plaintext secrets are denied in:

- GitHub;
- Google Drive;
- ChatGPT Library;
- Slack;
- chat;
- CASER documents;
- ordinary evidence logs.

Existing credentials may be consumed only inside an approved runtime/secret-handling path needed for an authorized operation. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

The dedicated Cloudflare ACME token is persisted only in DirectAdmin's provider configuration for the authorized DNS-01 integration. Its value is not stored in repository evidence. Standing authority applies only to unattended renewal of the existing `eimyherrer.com` + `*.eimyherrer.com` certificate through the existing DirectAdmin -> Cloudflare path and does not authorize unrelated DNS, credential, mail, hosting, or production changes.

If an endpoint's response surface may expose credential/session material and cannot be bounded before invocation, the endpoint remains blocked rather than relying on post-hoc redaction.

## Self-deployment boundary

The current self-deployment work remains staging-only.

Verified and completed within WB-0033 under separate explicit approvals:

- create the single DirectAdmin staging identity `staging.eimyherrer.com` on the existing shared-hosting account;
- create the single Cloudflare DNS-only A record for staging;
- store one dedicated zone-scoped Cloudflare ACME token in DirectAdmin;
- perform one manual wildcard renewal;
- read only production document-root path metadata required to prove non-overlap;
- authorize future unattended renewal only for the existing wildcard certificate through the existing DirectAdmin -> Cloudflare integration.

Still blocked unless a later separate authority is granted:

- staging application deployment / `staging_apply`;
- upload, overwrite, delete, mkdir/touch/cp/mv/rm, chmod/chown, symlink creation/replacement in staging application content;
- production application deployment or production content traversal/read;
- unrelated DNS changes, including apex, `www`, MX, TXT, mail records, or proxy-mode changes;
- mail, billing, VPS, WordPress, Nextcloud, registrar, package/service, PHP, ownership, or permission mutation;
- creation/changing/rotation/reset of credentials other than the already completed separately authorized ACME token action;
- reading or storing plaintext secrets in ordinary evidence channels;
- any broader production/provider mutation not covered by a new explicit operator approval.

WB-0033 does not itself grant application remote-write authority. A later staging-deployment work block requires a fresh, separate Jan Kočí remote-write authorization.

## Recent completed state changes

### PR #47 — WB-0029 disabled/manual staging workflow validator

Merged into `main` as:

```text
09750d7c5b2e49b9b4006c1288391d6d5c6066d5
```

Delivered a plan-only staging manifest, fail-closed staging target and manifest validator, manual `workflow_dispatch` dry-run workflow, tests for blocking `staging_apply`, no-remote-write receipt semantics, runbook, and kickoff evidence.

### PR #48 — PR47 post-merge state reconciliation

Merged into `main` as:

```text
dd389e87eb2684a4c90a816d35c0472e0b5e1fee
```

Recorded PR #47 / WB-0029 as merged, closed stale superseded PRs #42 and #46, and added next-slice planning docs and remote-write gate checklist.

### PR #49 — WB-0030 staging readiness gate

Merged into `main` as:

```text
2de294bb3334e4194769f3b883d58a2e5e3a8ea5
```

Delivered a fail-closed staging readiness gate, closed readiness evidence schema, hardened YAML preflight, manual `workflow_dispatch` readiness validator, regression tests for fail-closed bypass channels, runbook, audit evidence, and no-remote-write receipt semantics.

Verification recorded in the merge commit:

- exact head `334189a867ec071b085465cd1340e51e459c4bf6`;
- CI #135 PASS;
- CodeQL #132 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

### PR #50 — PR49 post-merge reconciliation and WB-0031 kickoff

Merged into `main` as:

```text
4a1374cbef7d142f8386ea7774208effc05d54ec
```

Recorded PR #49 / WB-0030 as canonical, defined WB-0031, and made deployment protocol / target capability an explicit runtime gate while keeping InterServer remote writes blocked.

Verification recorded in the merge commit:

- exact head `1f4e3544852a549a8f88ef14db4e35a305c15fcd`;
- CI #143 PASS;
- CodeQL #140 PASS;
- fresh Codex review: no major issues;
- all review threads resolved;
- manual AI review PASS.

### PR #51 — WB-0031 staging runtime gate preflight

Merged into `main` as:

```text
d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684
```

Delivered the local fail-closed deployment-protocol / target-capability preflight, closed evidence semantics, hardened target YAML parsing, regression coverage for duplicate/merge/anchor/alias/recursion/depth bypasses, and preserved the invariant that a local readiness PASS grants no remote-write authority.

Verification recorded in the merge commit:

- exact head `aa02ea82b7e86f851b60386b1d07f97d149912f8`;
- CI #166 PASS;
- CodeQL #163 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

### PR #52 — WB-0032 definition and kickoff

Merged into `main` as:

```text
304f4234e4f52c2375d904b45d1ed0c4fe31511c
```

Reconciled PR #51, defined WB-0032's two-phase model, and established the fresh Jan Kočí authority gate required before Phase B read-only provider discovery. It did not perform or authorize staging writes or production/provider mutation.

Verification recorded before merge:

- exact head `ed77854c4cbf128f9c2bcc4c8d8f09eb3d855adc`;
- CI #176 PASS;
- CodeQL #173 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

### PR #53 — WB-0032 Phase B documentation/preflight

Merged into `main` as:

```text
70346d63ba2b17df17085797e963bb9dbd692282
```

Converted the separately authorized read-only/non-mutating InterServer staging discovery authority into an explicit fail-closed provider procedure and preserved mutation boundaries until separate approvals were granted later in WB-0033.

## Current work block

### WB-0033 — InterServer Isolated Staging Target

PR #54 is the active terminal-evidence and canonical-state slice.

WB-0033 has established verified runtime evidence for:

- existing InterServer shared-hosting service identity;
- isolated DirectAdmin staging hostname and document root;
- separately authorized read-only production document-root path metadata and proven non-overlap;
- Cloudflare authoritative DNS and a DNS-only staging A record;
- external HTTP/HTTPS reachability;
- DirectAdmin Cloudflare ACME provider configuration;
- successful manual wildcard renewal through Cloudflare DNS-01;
- bounded standing authority for future unattended renewal of the existing wildcard certificate.

No CyberCore/application content has been deployed to staging. No production application content was read or mutated. Application remote write remains blocked.

The operator explicitly authorized finalization and squash merge of PR #54. That merge must still use exact-head verification and must not proceed if CI, CodeQL, Codex review, mergeability, or review-thread state becomes non-green.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- Monitor the wildcard certificate lifecycle and treat future unattended renewal as verified operational behavior only after a scheduled cycle is actually observed; standing authority already exists for that exact renewal path.
- The dedicated Cloudflare ACME token should remain least-privilege and zone-scoped; do not broaden it to unrelated zones or use a Global API Key without a separately justified change.
- Live staging application deploy remains blocked behind a fresh explicit remote-write authorization despite the now-verified target identity, DNS, TLS, and ACME path.

## Next action

Run exact-head CI, CodeQL, and adversarial Codex review for the canonical-state reconciliation on PR #54. Repair any valid finding. If the exact head remains mergeable and all gates are green, execute the already-authorized squash merge of PR #54 into `main` using the expected head SHA.

After merge, treat WB-0033 as the canonical verified staging-target baseline. Any actual CyberCore/application deployment to `staging.eimyherrer.com` must be opened as a later work block and requires fresh explicit staging remote-write authorization.

Do not broaden the existing approvals into unrelated provider, DNS, credential, application, or production mutation.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr54-wb0033-isolated-staging-target -->
## Manual repository checkpoint

- Generated: `2026-08-22T14:16:00+02:00`
- Branch: `wb-0033-interserver-isolated-staging-target`
- Pull request: #54
- Active artifact: `WB-0033`
- Active work block: `WB-0033 — InterServer Isolated Staging Target`
- Last verified main: `70346d63ba2b17df17085797e963bb9dbd692282`
- Staging target identity: VERIFIED
- Cloudflare authoritative DNS / staging A record: VERIFIED
- DirectAdmin -> Cloudflare ACME wildcard path: VERIFIED
- Production/staging document-root non-overlap: VERIFIED by bounded read-only metadata
- Standing wildcard unattended-renewal authority: granted for existing certificate/path only
- Staging application remote write allowed: false
- Production application write allowed: false
- Secret values recorded: false
- PR #54 merge authority: explicitly granted; exact-head gates still required
- Project Kernel: present
- Project State: WB-0033 verified; PR #54 finalization/merge gate active; application deployment remains blocked
<!-- CYBERCORE:CHECKPOINT:END -->
