# WB-0035 — InterServer VPS + Vikunja Bootstrap MOP

Status: `PREPARED — NO LIVE PROVIDER OR HOST MUTATION AUTHORIZED`

Target service hostname: `tasks.cyberdjs.org`

This MOP defines the intended order of operations after the separate WB-0035 authority gates are granted. It is not itself an approval to contact InterServer, order or pay for a VPS, change DNS, connect by SSH, modify a host, or deploy an application.

## Authority gates

- **A1 — catalog + quote:** read-only InterServer VPS catalog and quote only. No order, no payment.
- **A2 — purchase + payment:** exactly one approved VPS, bounded by the approved quote and spending limit.
- **A3 — bootstrap + deploy:** mutate only the newly created VPS. Existing shared hosting, mail, Nextcloud, website production and unrelated VPS resources remain out of scope.
- **A4 — DNS publication:** create or change only the explicitly approved `tasks.cyberdjs.org` record after the application is verified locally on the new VPS.

Each gate requires a fresh explicit operator approval. Approval of one gate does not imply the next.

## Phase 0 — repository preflight

1. Validate `.cybercore/provisioning/interserver-vps-plan.example.yaml`.
2. Run the WB-0035 unit tests.
3. Confirm plan invariants remain false for provider contact, order, payment, DNS, SSH mutation and application deployment.
4. Confirm `max_new_vps_count` is exactly `1` and recurring monthly budget is at most USD 3.00.
5. Confirm no plaintext secret is present in the plan, quote, receipt, PR or ordinary evidence.

Stop on any validation failure.

## Phase 1 — A1 catalog + quote

Only after A1 approval:

1. Read the current InterServer VPS catalog using the semantically reviewed read-only operation.
2. Validate the candidate configuration instead of auto-substituting a larger or more expensive plan.
3. Produce sanitized quote evidence with platform, slices, OS/version, location/stock, RAM/disk, recurring price, one-time price, quote reference, and explicit assertions that no order or payment occurred.
4. Run the plan+quote validator.
5. Generate an informational approval packet. The packet must keep `purchase_authorized=false` and `payment_authorized=false`.

Stop if monthly cost exceeds USD 3.00, an unexpected one-time cost exceeds the plan, resources are below the minimum, stock is unavailable, or the provider response is ambiguous.

## Phase 2 — A2 purchase

Only after an A2 approval bound to the exact quote:

1. Re-read enough account/service state to prove the intended service does not already exist.
2. Submit one VPS order only.
3. Do not blindly retry an ambiguous order response.
4. Record the returned non-secret service identifier and invoice/payment state.
5. Perform only the separately approved payment action and verify the charged amount against the packet.
6. Poll only the newly created service until `active`, terminal failure, or timeout.
7. Verify exactly one new intended VPS exists.

A failed application deployment does not authorize canceling or deleting a paid VPS. Cancellation is a separate provider mutation.

## Phase 3 — A3 host bootstrap

Only after the VPS identity, public IP and access path are verified and A3 is approved:

1. Verify the SSH host key/fingerprint out of band before managed access.
2. Establish key-based operator access and verify recovery access before reducing root/password access.
3. Patch the operating system.
4. Create a dedicated administration/deploy identity where practical.
5. Apply inbound default-deny firewall policy with only the approved SSH path plus HTTP/HTTPS when needed.
6. Install Docker Engine and the Compose plugin from an approved source.
7. Create persistent directories:
   - `/srv/vikunja/files`
   - `/srv/vikunja/db`
   - `/srv/vikunja/backups`
   - `/srv/vikunja/caddy_data`
   - `/srv/vikunja/caddy_config`
8. Set ownership for the Vikunja data directories so container user `1000` can write to `files` and `db`.
9. Materialize the Vikunja service secret only through the approved runtime secret path. Do not store the value in Git, chat, Drive, Slack, CASER or ordinary evidence.
10. Resolve and pin exact Vikunja and Caddy image digests before running Compose. Floating `latest` is not acceptable.

Stop before any step that risks operator lockout without a tested fallback path.

## Phase 4 — local-only Vikunja verification

Still under A3, before public DNS:

1. Copy the reviewed deployment template and runtime references to the new VPS.
2. Start **only** the `vikunja` service first.
3. The template binds Vikunja to `127.0.0.1:3456`; it must not be publicly reachable directly.
4. Verify locally over the SSH session that the service responds on `http://127.0.0.1:3456`.
5. Verify `/srv/vikunja/db/vikunja.db` and `/srv/vikunja/files` are persistent host paths.
6. Restart the Vikunja container and confirm the database and application state survive.
7. If initial registration is temporarily enabled, create only the intended bootstrap accounts and then set registration back to disabled unless a later decision explicitly keeps it open.

Do not start Caddy as part of this phase unless A4 and the public hostname prerequisites are satisfied.

## Phase 5 — backup and restore gate

Before treating the service as durable:

1. Stop Vikunja cleanly for the first SQLite backup verification.
2. Create a timestamped backup of the SQLite database and uploaded files under `/srv/vikunja/backups`.
3. Record hashes and non-secret metadata for the backup.
4. Restore into an isolated temporary path or disposable validation instance, not over the live data.
5. Verify the restored database can be opened by Vikunja and expected bootstrap objects are present.
6. Restart the live service only after backup creation completes successfully.

A backup that has not been restore-tested is not considered verified.

## Phase 6 — A4 DNS + HTTPS

Only after local application health, persistence and restore readiness are verified and A4 is explicitly approved:

1. Confirm the exact new VPS public IP.
2. Create or modify only the approved `tasks.cyberdjs.org` DNS record.
3. Verify authoritative/public DNS resolution.
4. Start the `caddy` service.
5. Verify HTTPS certificate issuance and `https://tasks.cyberdjs.org/` reachability.
6. Verify Vikunja's configured public URL exactly matches `https://tasks.cyberdjs.org/`.
7. Confirm port `3456` remains loopback-only and the public application path is only through Caddy on 443.

## Effect verification

PASS requires all applicable checks:

- one intended VPS exists and no duplicate order occurred;
- actual recurring price matches the approved quote;
- SSH identity is verified;
- firewall exposure matches the approved ports;
- Vikunja is reachable locally and later through HTTPS;
- SQLite and uploaded files survive container restart;
- backup creation and isolated restore test succeed;
- registration state matches the approved policy;
- no plaintext secrets entered ordinary evidence;
- no existing shared-hosting, mail, Nextcloud, website production or unrelated VPS resource was mutated.

## Rollback boundaries

- **Repository-only:** revert the branch/PR changes.
- **Before purchase:** stop; there is no provider rollback because no mutation occurred.
- **After purchase:** do not infer cancellation from a failed bootstrap. Preserve the service and request a separate provider-mutation decision.
- **Host bootstrap:** restore only changed configuration on the new VPS when the rollback action is known and bounded; preserve operator access.
- **Application:** stop/remove the Vikunja/Caddy containers while preserving `/srv/vikunja` data unless an explicit destructive rollback is approved.
- **DNS:** revert only the exact `tasks.cyberdjs.org` record created/changed under A4 when that rollback is explicitly authorized.

When rollback scope is ambiguous, stop and preserve state for review rather than deleting resources.
