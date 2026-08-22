# WB-0032 — InterServer Staging Capability Discovery

## Status

Definition active. Provider-contact execution is **not authorized** by this document or by the kickoff PR that creates it.

## Canonical base

- Repository: `cyberDJs/CyberCore`
- Base: `main@d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- Predecessor: `WB-0031 — Staging Runtime Gate Preflight`
- Predecessor PR: #51, merged as `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- Accepted architecture boundary: `ADR-0006 — Self-Deployment Staging Boundary`

## Goal

Convert the remaining InterServer staging unknowns into safe, non-secret, evidence-backed runtime facts before the first remote write.

WB-0032 is a **discovery** work block. It must not mutate the provider, staging content, production content, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, credentials, or any other production/provider state.

## Two-phase execution model

### Phase A — repository kickoff

The kickoff PR may only:

- reconcile canonical state after PR #51;
- define this work block and its evidence contract;
- keep all real provider facts `UNKNOWN_UNTIL_VERIFIED` until observed;
- define the separate authority gate required before any live InterServer contact.

Phase A performs **no InterServer connection** and handles **no secret values**. No approval may broaden the kickoff PR beyond this repository-only scope.

### Phase B — live read-only capability discovery

Phase B may begin only after a fresh explicit authorization from **Jan Kočí** that names the target/provider scope and confirms read-only discovery.

A Phase B authorization must not be interpreted as authority for `staging_apply`, upload, file creation, file modification, credential rotation, provider setting changes, or production mutation. No approval may broaden WB-0032 into a mutating work block.

## Runtime questions to resolve

The later read-only discovery must establish evidence for all of the following without assuming any answer in advance:

1. **Staging identity**
   - non-production staging domain or URL;
   - staging document root or isolated path;
   - evidence that the path is not the production document root for `eimyherrer.com`.
2. **Deployment protocol / target capability**
   - whether SSH is available;
   - whether rsync is usable over SSH;
   - whether SFTP is available;
   - whether an InterServer/provider-native deployment mechanism is available and appropriate;
   - the least-privilege deployment-user scope actually available.
3. **Secret readiness without disclosure**
   - whether required secret aliases can be resolved from an approved secret store;
   - whether the credential material is usable for the approved read-only probe;
   - no plaintext secret value may be copied into GitHub, chat, Drive, Slack, CASER documents, or ordinary logs.
4. **Rollback capability**
   - whether immutable release directories and a `current` symlink are supported;
   - otherwise whether timestamped backup-before-overwrite is practical;
   - otherwise whether a no-overwrite upload to a new staging path is practical;
   - if no safe rollback path exists, future remote write remains blocked.
5. **Effect-verifier capability**
   - a safe staging health URL or equivalent non-mutating verifier;
   - a version/commit marker strategy that does not require production mutation;
   - checks capable of proving production was not changed.
6. **Credential-rotation operational state**
   - record only non-secret state such as `unknown`, `verified`, dates, aliases, owner, or safe fingerprint/hash where appropriate;
   - credential rotation itself is outside WB-0032 and cannot be added to Phase B; any future rotation requires a separate work block or procedure plus its own explicit authorization.

## Evidence contract

Evidence produced by Phase B may contain only non-secret facts such as:

- target/provider identifiers;
- sanitized host or URL identifiers when safe;
- non-secret path identity when approved for evidence storage;
- supported protocol names;
- capability booleans/statuses;
- secret aliases and presence/readiness status only;
- safe fingerprints/hashes where appropriate;
- timestamps;
- Jan Kočí authorization reference;
- rollback capability result;
- verifier capability result;
- commands/actions performed in sanitized form;
- explicit `remote_write_performed: false` and `secret_values_recorded: false` assertions.

Evidence must not contain passwords, private keys, API tokens, cookies, TOTP seeds, recovery codes, session material, or other plaintext credentials.

## Read-only authority boundary

Before the first live InterServer contact, a fresh explicit authorization from **Jan Kočí** must specify:

- provider/target: InterServer staging only;
- purpose: capability discovery;
- access mode: read-only/non-mutating;
- permitted protocol or probe class;
- explicit prohibition on upload, overwrite, deletion, chmod/chown, symlink creation, provider configuration changes, credential rotation, and production access;
- secret handling: aliases/references only in ordinary evidence; values remain inside approved secret storage/runtime handling;
- stop condition: abort on ambiguity about staging-vs-production identity or command mutability.

No authorization from PR #51, ADR-0006, or the WB-0032 kickoff PR satisfies this Phase B gate. Only a fresh explicit authorization from Jan Kočí may enable the read-only discovery described here; it cannot authorize mutation.

## Safety invariants

Throughout WB-0032:

- `remote_write_requested: false`;
- `remote_write_allowed: false`;
- `production_write_allowed: false`;
- `staging_apply` remains blocked;
- credential rotation remains outside the work block;
- real provider capability remains `UNKNOWN_UNTIL_VERIFIED` until observed under the approved Phase B procedure;
- target metadata, documentation, aliases, and synthetic tests are not proof of live provider capability.

## Exit criteria

WB-0032 can be considered complete only when:

- PR #51 is reconciled as merged into canonical `main@d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`;
- this work block is canonical and its authority boundary is explicit;
- a read-only discovery separately authorized by Jan Kočí has established the real non-production target identity;
- deployment protocol and target capability are evidenced without remote write;
- required secret aliases are evidenced as ready without secret disclosure;
- rollback capability is evidenced;
- effect-verifier capability is evidenced;
- credential-rotation operational state is recorded safely without performing rotation;
- all evidence states explicitly record that no remote write occurred and no secret values were stored;
- a later `staging_apply` work block remains separately gated by fresh explicit Jan Kočí authorization.

The kickoff PR for WB-0032 stops before Phase B and therefore does not by itself satisfy these exit criteria.
