# WB-0034 Explicit FTPS Path-Scoped Security Review

Date: 2026-08-29
Decision: `ACCEPT WITH RUNTIME GATES`
Related ADR: `ADR-0007`
Target: `interserver-shared-hosting-staging`

## Evidence reviewed

- Canonical GitHub `main` at `090433264f4338828db293a327d5083bacf1813f`.
- WB-0034 first-write MOP and readiness contract.
- Runtime read-only SSH/SFTP probe: existing `eimyherr` identity authenticates successfully and has staging write capability.
- Runtime scope probe: the same identity also has production document-root write capability.
- DirectAdmin documentation for custom-path FTP accounts.
- InterServer documentation for explicit FTP over TLS.

No secret values are included in this review.

## Threat model

### T1 — credential compromises production

Risk: a production-wide hosting credential used by automation can write outside staging.

Control: use a dedicated DirectAdmin `custom` FTP account whose server-side root is exactly the canonical staging document root. Production-wide SSH/SFTP credential reuse is denied.

### T2 — plaintext FTP downgrade

Risk: credentials or payloads cross the network without TLS.

Control: protocol identity is `FTPS_EXPLICIT`; the client must require `AUTH TLS`, reject plaintext fallback, and fail closed if TLS negotiation fails.

### T3 — TLS interception or hostname mismatch

Risk: encryption without authentic server identity permits interception.

Control: certificate verification and hostname verification are mandatory. The runtime must use the InterServer server hostname covered by the FTPS certificate; a certificate error is a hard stop.

### T4 — incorrect DirectAdmin path scope

Risk: the account is configured above staging or can traverse outside its effective root.

Control: authenticated read-only verification must prove the effective account root and demonstrate that the production document root is outside the visible/writeable namespace. Configuration claims alone are insufficient.

### T5 — FTPS passive data-channel escape/failure

Risk: the command channel succeeds but data-channel behavior is unverified or requires unsafe firewall workarounds.

Control: capability verification must include passive-mode directory metadata/list behavior through TLS without server/firewall mutation. Any need for provider firewall mutation is a separate authorization boundary.

### T6 — secret leakage

Risk: FTP password appears in repository, logs, evidence, process arguments, or chat.

Control: only a secret alias/locator may enter ordinary evidence. Runtime password retrieval must use approved OS-backed secret storage or an approved external vault. Diagnostic commands must not echo the value.

## Required runtime evidence before READY

1. `protocol = FTPS_EXPLICIT`.
2. `AUTH TLS` is required and plaintext fallback is disabled.
3. Server certificate chain and hostname verification pass.
4. Effective account root equals `/home/eimyherr/domains/staging.eimyherrer.com/public_html`.
5. Production document root is not traversable or writeable by the FTPS identity.
6. Passive-mode metadata/list operation succeeds without remote mutation.
7. Secret alias exists without value disclosure.
8. Rollback semantics remain exact-run-directory scoped.
9. Effect verifier is implemented and dry-run verified.
10. Final packet and same-process uploader support `FTPS_EXPLICIT` explicitly.
11. Fresh operator approval binds the exact FTPS endpoint identity and deploy scope.

## Denied states

- plain `FTP`;
- opportunistic `FTP_TLS_IF_AVAILABLE`;
- `--insecure`, disabled peer verification, or hostname verification bypass;
- existing `eimyherr` production-capable SSH key as automatic fallback;
- account root `/home/eimyherr` or any parent of the staging root;
- storage of password/private credential material in repository or evidence;
- remote account creation, upload, delete, chmod/chown, provider, DNS, production, or firewall changes under this review alone.

## Verdict

The path-scoped explicit-FTPS design is safer than reusing the verified production-capable SSH/SFTP identity and is acceptable for WB-0034 provided all runtime gates above remain fail-closed. The design is not deployment authorization and does not by itself make the current WB-0034 packet READY.