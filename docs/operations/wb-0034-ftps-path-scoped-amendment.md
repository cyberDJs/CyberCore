# WB-0034 — Explicit FTPS Path-Scoped Amendment

Date: 2026-08-29
Status: `DESIGN + VALIDATOR SUPPORT — REMOTE WRITE BLOCKED`
Parent: `WB-0034 — First Staging Deployment Preflight`
Decision: `ADR-0007`
Target: `interserver-shared-hosting-staging`

## Reason for amendment

The original WB-0034 protocol gate allowed only `SFTP` or `SSH`. Runtime read-only verification proved that the existing `eimyherr` SSH/SFTP identity can write both the staging and production document roots. It therefore fails the WB-0034 least-privilege requirement for an automated first-write runner.

The selected fallback is a DirectAdmin custom-path account restricted to the canonical staging document root and used only through explicit FTP over TLS.

## Protocol identity

The machine protocol token is:

```text
FTPS_EXPLICIT
```

It means all of the following:

- FTP control connection with mandatory explicit TLS upgrade (`AUTH TLS`);
- plaintext FTP fallback disabled;
- certificate chain verification enabled;
- certificate hostname verification enabled;
- passive data connections protected by TLS;
- endpoint hostname must be the InterServer server hostname covered by the certificate;
- authentication uses a dedicated path-scoped DirectAdmin FTP identity.

The following are not aliases for `FTPS_EXPLICIT` and remain denied:

```text
FTP
FTPS_IMPLICIT
FTP_TLS_IF_AVAILABLE
```

Any client option that disables certificate or hostname verification keeps the runtime gate BLOCKED.

## Deploy identity scope

Before `deploy_identity_scope_status` may become `VERIFIED`, authenticated read-only evidence must prove:

1. the account's effective root is exactly `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
2. the account cannot traverse to or write `/home/eimyherr/domains/eimyherrer.com/public_html`;
3. passive-mode directory metadata/listing works over TLS without remote mutation;
4. no provider, firewall, DNS, ownership, permission, or service mutation was needed for the probe.

A DirectAdmin configured-path claim by itself is not sufficient evidence.

## Secret alias compatibility

WB-0034 retains the existing four secret aliases for this amendment to avoid widening the change surface:

- `INTERSERVER_STAGING_HOST`;
- `INTERSERVER_STAGING_USER`;
- `INTERSERVER_STAGING_PORT`;
- `INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD`.

For `FTPS_EXPLICIT`, the last alias is a legacy-named compatibility alias and must resolve only to the dedicated path-scoped FTPS account password in approved secret storage. It must not resolve to the existing production-capable SSH private key or a production-wide hosting password.

A future cleanup may rename this alias in a separately reviewed schema migration. No secret value may appear in GitHub, chat, Drive, CASER evidence, command-line arguments, or ordinary logs.

## Validator amendment

The WB-0034 readiness and evidence validators may accept exactly these verified protocol values:

```text
SFTP
SSH
FTPS_EXPLICIT
```

Evidence and operator authorization must still use the same protocol token. `FTPS_EXPLICIT` does not weaken any existing artifact, source-commit, destination, rollback, secret, evidence-bundle, or fresh-authorization invariant.

## Runtime still blocked

This amendment does not make the first write READY. Before a final authorization packet can be assembled, all original WB-0034 gates still apply plus the FTPS-specific gates:

- dedicated custom-path identity provisioned under separate authorization;
- secret aliases safely provisioned;
- authenticated read-only FTPS capability and scope verification;
- TLS certificate/hostname verification evidence;
- passive data-channel verification;
- rollback runtime verification;
- effect verifier implementation and dry run;
- same-process Phase-B uploader support for `FTPS_EXPLICIT`;
- exact trusted-main source commit and artifact hashes;
- fresh explicit first staging remote-write authorization.

## No authority expansion

This amendment does not authorize:

- DirectAdmin account creation or password creation;
- credential storage or rotation;
- any remote mkdir/upload/delete/chmod/chown;
- `staging_apply`;
- production access or mutation;
- DNS/TLS/provider/firewall mutation;
- automatic or recurring deployment.

If FTPS cannot prove the required staging-only root and verified TLS behavior, the correct result is `BLOCKED`; the runner must not silently fall back to the existing `eimyherr` SSH/SFTP identity.