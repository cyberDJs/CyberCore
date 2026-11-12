# ADR-0015: Governed MCP path for Nextcloud R1 off-host transfer

Status: Proposed in isolated Draft PR; no merge or deployment authorization.

## Context

Issue #113 has a verified off-host database copy and isolated database restore rehearsal, but the full Nextcloud application/data archive remains on the production failure domain. Manual creation of temporary SSH credentials is operationally brittle, while exposing a generic shell through the CyberCore MCP tunnel would violate the existing execution boundary.

CyberCore already has:

- identity-bound MCP room tunnels;
- an allowlist-only backend tool mechanism;
- a governed SSH subsystem with `shell=False`;
- exact target/plan/authorization binding and execution receipts;
- deny-all mutation authorization unless a real verifier is configured.

## Decision

Add a narrowly scoped Nextcloud R1 capability rather than a shell.

The MCP surface is conditional and identity-bound:

- handler name: `nextcloud.r1.offhost`;
- MCP tool: `cyberdjs.room.nextcloud_r1`;
- it is registered only when the backend explicitly exposes the handler;
- intended runtime composition is Johnny Work only;
- action is one of `transfer`, `status`, `verify`;
- callers cannot choose hostnames, paths, users, ports, commands or SSH options.

The execution target is fixed to `cyberskills-vps` (`162.35.186.106`). The transfer operation starts one preinstalled static unit asynchronously. The unit executes a fixed Python helper as `cybercore-exec`, reads a dedicated transfer credential from a fixed private path, performs a fixed SCP/SFTP pull, validates size and gzip integrity, requires a separately observed fixed source SHA-256 and compares
the transferred bytes against it before atomic publication, then writes a non-secret receipt. Verification independently re-hashes the off-host copy and checks required archive component markers.

The repository does not contain or mint the credential. Credential provisioning/revocation remains a separately approved deployment step and must use a dedicated source identity, not an existing production key.

## Security invariants

- no generic shell or caller-defined argv;
- no `bash -c`, `sh -c`, `eval`, pipe or redirection construction;
- no arbitrary SSH target or source path;
- no agent forwarding;
- strict host-key checking;
- transfer identity is dedicated and restricted;
- raw authorization reference is never returned in receipts;
- mutation remains deny-all without two valid short-lived exact approval manifests (client and server);
- MCP capability is absent unless runtime composition explicitly injects the handler;
- Eimy and Johnny Moderator do not receive the handler by default;
- the governed Johnny Work broker socket requires an explicit OS peer UID and rejects other Unix peers before request parsing;
- the governed frontend UID must be non-root and distinct from the broker UID;
- deployment and production restore remain separately authorized actions.

## Alternatives rejected

1. Generic remote shell over MCP — too much authority and hard to audit.
2. Reuse an existing production SSH key — violates least privilege and the #113 transfer boundary.
3. Stream the 13 GB archive through a laptop — dependent on a mobile device and operationally unreliable.
4. Put a private key in GitHub, MCP arguments or evidence — unacceptable secret exposure.

## Consequences

The design adds a second fixed governed execution target, a short-lived file-bound exact approval
verifier, and a small target-specific deployment candidate. It does not deploy anything. A future
deployment still needs fresh approval provenance, matching root-owned manifests on both sides,
restricted credential provisioning, exact-host verification, peer-UID/socket-ACL verification, and
independent post-deployment tests.


## Additional deployment trust gates

A path-specific Unix socket alone is not sufficient authentication for a mutating capability.
The candidate therefore adds an OS peer-credential gate to the broker. When the Nextcloud R1 handler
is composed, the runtime requires an explicit positive non-root Johnny Work UID that differs from
the broker UID. Every connection on that governed socket is rejected before request parsing unless
the kernel-reported peer UID matches.

Deployment must run the Johnny Work frontend under that dedicated Unix identity and grant only that
identity the minimum filesystem/ACL permission needed to connect to its socket. Eimy, Johnny
Moderator, and the broker identity must not share that UID. If the host cannot provide trustworthy
Unix peer credentials or a narrow socket ACL, governed mutation remains BLOCKED.

The source checksum is also external evidence: deployment must obtain the SHA-256 from the exact
source archive independently before transfer and place only that non-secret digest into the fixed
`source_archive.sha256` file. Target-only hashing is insufficient evidence of source-to-target
identity.


## Exact approval binding

The #113 candidate implements a file-bound verifier rather than treating a non-empty approval
reference as authority. The manifest stores only the SHA-256 of the raw approval reference and the
exact governed tuple. The verifier rejects:

- missing or extra schema fields;
- wrong operation/target/plan/revision;
- approval-reference digest mismatch;
- symlinked or non-regular manifest files;
- unexpected owner or group/world-writable file/directory;
- non-UTC timestamps;
- expired/not-yet-valid approvals;
- validity windows longer than one hour.

The server entrypoint selects this verifier only for the fixed `cyberskills-vps` target. The
existing `tasks.cyberdjs.org` target retains deny-all behavior. Client composition uses the same
verifier contract from the fixed Johnny Work approval path. The repository contains no live
approval manifest, so this Draft PR itself grants no execution authority.


## Rollback operation boundary

The operation family includes `nextcloud.r1.offhost.rollback` as a fixed local containment action.
It starts a sandboxed static systemd unit that conflicts with the transfer unit, removes only known
local partial/credential artifacts, preserves the final archive and transfer receipt, and emits a
non-secret receipt.

It deliberately does not issue a source-host revoke command. Remote public-key cleanup remains an
explicit deployment closeout requirement and is surfaced as unresolved in the rollback receipt.
