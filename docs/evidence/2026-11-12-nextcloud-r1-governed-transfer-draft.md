# Nextcloud R1 governed transfer Draft PR evidence

Date: 2026-11-12

## Authorization

User-authorized repository scope:

```text
APPROVE CYBERCORE GOVERNED MCP EXECUTION: prepare an isolated Draft PR extending
the existing governed execution bridge with a narrowly scoped Nextcloud R1
off-host backup operation for #113; fail-closed, fixed targets/paths, no generic
shell, no arbitrary SSH, no credential disclosure, exact approval binding,
receipts, tests and rollback. No merge and no deployment.
```

## Source-of-truth preflight

- repository: `cyberDJs/CyberCore`;
- branch base: `main@ae2f4572df74bf2cc49228ce88aab1f9b0e5fb42`;
- active parallel Draft PR #159 was observed before branching;
- isolated branch:
  `draft/nextcloud-r1-governed-transfer-20261112`;
- issue #113 remained open;
- no merge or deployment authority was inferred.

## Candidate design

- fixed execution target: `cyberskills-vps-nextcloud-r1` / `162.35.186.106`;
- fixed source: `eimyherr@162.250.126.107`;
- fixed archive identity and destination;
- fixed operation allowlist;
- no free-form execution arguments;
- MCP room tool carries only operation/plan/revision/authorization binding;
- actual authorization remains delegated to a trusted verifier;
- source key is forced-command/restricted and self-revoking;
- target helper validates source SHA-256 against streamed SHA-256 before atomic
  promotion;
- rollback preserves a verified final archive.

## Local isolated checks performed before PR opening

Inside an isolated local candidate workspace:

- Python syntax compilation passed for transfer, rollback and source-export helpers;
- policy/protocol/operation contract smoke test passed;
- wrong target was rejected by the operation allowlist.

These checks are builder evidence only. They are not independent verification.

## Deployment state

```text
MERGE = NOT_AUTHORIZED
DEPLOY = NOT_AUTHORIZED
PRODUCTION_MUTATION = FALSE
CREDENTIAL_CREATED = FALSE
SOURCE_AUTHORIZED_KEYS_CHANGED = FALSE
TARGET_VPS_CHANGED = FALSE
```

CI, CodeQL and independent PR review are required before `READY_FOR_MERGE`.
