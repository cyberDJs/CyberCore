# InterServer Staging Target Preflight

Date: 2026-08-19
Work block: `WB-0028`

## Preflight objective

Before CyberCore can deploy to InterServer staging, the target must be proven safe, isolated, reversible, and non-secret.

## Required answers

| Field | Required state |
|---|---|
| Staging URL | Known non-production URL |
| Staging path | Known non-production document root |
| Production path | Known only enough to avoid it; no secret data |
| Deploy method | SSH/rsync, SFTP, or provider-native |
| Deploy identity | Staging-only identity |
| Secret aliases | Present in approved storage |
| Rollback | Known and tested or deployment blocked |
| Effect verifier | Known health check and version marker |

## Fail-closed conditions

Block deployment if any are true:

- staging path is unknown;
- staging path may overlap production;
- deploy identity can mutate production;
- production credentials would be reused;
- rollback method is unknown for a nontrivial change;
- effect verifier is missing;
- operator has not authorized the first remote write.

## Safe evidence

Allowed:

- provider name;
- target id;
- non-secret staging URL;
- non-secret path labels;
- secret aliases;
- verification status.

Denied:

- passwords;
- SSH private keys;
- API tokens;
- TOTP seeds;
- session cookies;
- recovery codes.