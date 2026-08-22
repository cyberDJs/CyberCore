# WB-0033 DirectAdmin staging-create evidence

Date: 2026-08-22
Work block: `WB-0033`
Target: `staging.eimyherrer.com`
Provider: InterServer shared hosting / DirectAdmin
Authoritative DNS: Cloudflare

## Result

`VERIFIED`

Observed runtime facts from the operator-executed guarded apply and subsequent DNS/TLS verification:

- DirectAdmin server: `vda7600.is.cc:2222`
- DirectAdmin user: `eimyherr`
- API login: HTTP 200
- temporary cookie session established: yes
- temporary login key created: no
- create endpoint: `/CMD_SUBDOMAIN`
- create response: HTTP 200
- target existed before: no
- target present on readback: yes
- requested staging document root: `/domains/staging.eimyherrer.com/public_html`
- normalized staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- production application content read: no
- production content mutated: no
- application deployed: no
- DirectAdmin session logout: HTTP 200

## Correction to earlier auth observations

Earlier DirectAdmin password-auth probes returned 401 because the operator had entered the InterServer API key at a prompt requesting the DirectAdmin password. Those 401 observations therefore do not establish `api_with_password=no` or an invalid DirectAdmin password.

The separate `/CMD_LOGIN` HTTP 410 observation remains evidence that the legacy login route used by the v2 helper was not valid for this server. The corrected v3 helper used the server-advertised `/api/login` flow and authenticated successfully with the existing DirectAdmin password.

## External DNS verification

The operator confirmed that authoritative DNS for `eimyherrer.com` is Cloudflare, not InterServer DNS.

Read-only Cloudflare API discovery established:

- API token validity: PASS
- zone lookup for `eimyherrer.com`: PASS
- DNS read: PASS
- `staging.eimyherrer.com` before create: absent
- verified InterServer origin A address: `162.250.126.107`

After explicit operator authorization for the single DNS mutation, exactly one record was created:

- type: `A`
- name: `staging.eimyherrer.com`
- content: `162.250.126.107`
- proxied: `false` / DNS only

Post-create verification established:

- Cloudflare API readback: one matching A record
- public resolver `1.1.1.1`: `162.250.126.107`
- no MX, TXT, mail, apex, `www`, or unrelated DNS record was changed

## HTTP and TLS verification

Observed after DNS convergence:

- `http://staging.eimyherrer.com`: HTTP 200
- `https://staging.eimyherrer.com`: HTTP 200
- remote origin observed: `162.250.126.107`
- TLS verify result: `0`

The initially served certificate was a valid Let's Encrypt wildcard certificate covering:

- `*.eimyherrer.com`
- `eimyherrer.com`

## DirectAdmin / Cloudflare ACME integration

DirectAdmin read-only discovery confirmed the target server exposes the Cloudflare ACME DNS provider.

Observed provider capability:

- `cloudflare_available: True`
- configured provider before setup: none
- supported token field includes `CLOUDFLARE_DNS_API_TOKEN`

After separate explicit operator authorization, a dedicated Cloudflare ACME DNS token scoped to the `eimyherrer.com` zone was stored in DirectAdmin as `CLOUDFLARE_DNS_API_TOKEN`.

Sanitized DirectAdmin readback established:

- ACME config present: true
- configured provider: `cloudflare`
- DNS token saved: true
- token value printed or stored in evidence: false

## Wildcard renewal end-to-end verification

After separate explicit operator authorization, one manual wildcard renewal was executed through DirectAdmin using the configured Cloudflare DNS provider.

Post-renewal certificate observation:

- serial: `0565366A39E1BF20BA2F0ABB1988F1CA8E55`
- subject: `CN=eimyherrer.com`
- issuer: Let's Encrypt `YE2`
- notBefore: `Aug 22 10:05:28 2026 GMT`
- notAfter: `Nov 20 10:05:27 2026 GMT`
- SANs: `*.eimyherrer.com`, `eimyherrer.com`

Post-renewal staging verification:

- `https://staging.eimyherrer.com`: HTTP 200
- remote origin: `162.250.126.107`
- TLS verify result: `0`

This proves the current DirectAdmin -> Cloudflare DNS API -> Let's Encrypt DNS-01 wildcard issuance path end-to-end.

## Production/staging non-overlap verification

After Codex identified that the earlier evidence did not contain canonical production-path metadata, the operator separately authorized a narrowly scoped read-only DirectAdmin document-root metadata read for `eimyherrer.com`, explicitly without reading production application content.

Observed DirectAdmin metadata:

- production document root: `/home/eimyherr/domains/eimyherrer.com/public_html`
- staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- same path: false
- staging inside production: false
- production inside staging: false
- production application content read: false

This closes the production-overlap evidence gap without traversing or reading production application files.

## Standing ACME renewal authorization

The operator separately granted standing authorization for future unattended automatic renewal of the existing `eimyherrer.com` + `*.eimyherrer.com` certificate through the existing DirectAdmin -> Cloudflare ACME integration.

This standing authority is limited to renewal of that same certificate identity through the existing provider path. It does not authorize unrelated DNS changes, new certificate identities, provider changes, additional credential mutation, or application/production mutation.

## Review verification

Codex first reviewed exact head `fc410957e61c1c62a0fd59d1802c2302d93e2c41` and raised two P1 governance findings plus one P2 handoff finding. The operator supplied the missing bounded authorizations/evidence, the branch was reconciled, and the prior review threads were resolved.

A fresh Codex review of exact head `82b90ca2ee7097d3959a2d4bfd0eeb60a2d9729d` reported no major issues. On that head:

- CI #190: PASS
- CodeQL #187: PASS
- Python 3.11/3.12/3.13/3.14: PASS
- Ruff lint/format: PASS
- Pyright: PASS
- package build/wheel smoke: PASS

The operator then explicitly authorized finalization and merge of PR #54. Final documentation-only reconciliation commits made after that review require the repository's exact-head gates to be rechecked before executing the approved merge.

## Safety assertions

- plaintext credentials recorded: false
- session cookie values recorded: false
- login URL value recorded: false
- Cloudflare token values recorded: false
- production application content read: false
- production content mutated: false
- unrelated DNS records mutated: false
- application deployed: false
- new paid hosting service ordered: false

## Final status

`VERIFIED — MERGE AUTHORIZED, EXACT-HEAD RECHECK REQUIRED AFTER FINAL DOC RECONCILIATION`

The isolated staging target is externally resolvable, serves HTTP/HTTPS successfully, has a verified wildcard ACME path through DirectAdmin with Cloudflare as authoritative DNS, and is proven path-isolated from production without production application-content access.
