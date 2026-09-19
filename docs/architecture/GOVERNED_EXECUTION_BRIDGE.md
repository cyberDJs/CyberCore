# Governed Execution Bridge V1

Status: repository repair under review; not deployed
Work block: `WB-0037` with `WB-0038E` execution-boundary repair

## Purpose

WB-0037 connects a bounded CyberCore action that has already passed continuity,
governance, and approval checks to an execution transport without creating a
general-purpose remote shell. WB-0038E repairs the client/server protocol,
timeout, privilege, receipt-disclosure, and rollback contracts before this
boundary can be considered deployable.

The first target is only `tasks.cyberdjs.org` (`162.35.117.219`). The first
operation family is only Vikunja operations required by A6.

## V1 flow

```text
Cyber Voice READY / bounded CommandPlan
  -> governed execution policy
  -> exact target + operation + plan binding
  -> SSH subsystem transport
  -> server-side cybercore-exec subsystem
  -> execution receipt
  -> separate independent verifier
```

## Why an SSH subsystem

OpenSSH normally executes a supplied remote command through the account's login
shell. That would violate the `shell=false` execution boundary even if the local
client used `subprocess.run(..., shell=False)`.

V1 therefore requests the dedicated `cybercore-exec` SSH subsystem using
`ssh -s`. The client sends one canonical JSON request on stdin. The server-side
subsystem parses that request and maps the operation to its own fixed argv. It
must not evaluate request fields as shell text.

The subsystem is not deployed or activated by WB-0038E.

## Canonical target

```text
target_id: tasks.cyberdjs.org
hostname: 162.35.117.219
ssh_user: cybercore-exec
subsystem: cybercore-exec
```

The target is compiled into policy. V1 does not accept caller-selected hosts,
users, ports, subsystems, or arbitrary paths.

## Supported operations

```text
vikunja.backup.install
vikunja.backup.run
vikunja.backup.status
vikunja.health.verify
```

V1 accepts no free-form arguments for these operations. Any extra argument key
fails closed.

## Required binding

Every request must carry:

- exact protocol `version: 1`;
- `operation_id`;
- exact `target_id`;
- exact `plan_id` and `plan_revision`;
- `authorization_reference`;
- one supported operation.

Client and server import the same protocol-version constant. Unsupported or
mistyped versions fail closed.

The bridge does not mint or infer authorization. The authorization verifier that
precedes this bridge remains authoritative.

## Transport invariants

The local transport uses an argv vector and `subprocess.run(..., shell=False)`.
It requests an SSH subsystem rather than a remote command. Batch mode,
`IdentitiesOnly`, strict host-key checking, and a connection timeout are fixed
in the transport argv.

The total SSH transport timeout must exceed the connection timeout plus the
largest server operation budget. WB-0038E uses a 180-second transport timeout for
a 15-second connection timeout and a 120-second maximum server operation timeout.

V1 deliberately does not support:

- arbitrary shell commands;
- `bash -c`, `sh -c`, or equivalent wrappers;
- caller-selected SSH hosts or users;
- command substitution or metacharacter interpretation;
- arbitrary sudo;
- arbitrary filesystem paths.

## Privilege boundary

Mutating operations do not call `systemd-run` or accept caller-defined unit
properties. Bootstrap installs two root-owned static wrapper units:

- `cybercore-vikunja-backup-install.service`;
- `cybercore-vikunja-backup-run.service`.

The bootstrap manifest reloads systemd before installing the Polkit rule. The
Polkit rule allows the `cybercore-exec` identity to request only `start` for
those exact wrapper names. Because the static unit fragments already exist when
authorization becomes available, the names cannot be reused for an arbitrary
transient service.

Rollback removes the privilege rule before removing either static wrapper and
reloads systemd after the wrapper files are removed.

## Execution receipt

The server receipt records only non-secret execution metadata:

- operation and target binding;
- plan/revision;
- SHA-256 binding of the authorization reference, not the raw reference;
- start and completion timestamps;
- exit code;
- SHA-256 digests of stdout and stderr;
- whether mutation was possible.

Raw stdout/stderr and the raw authorization reference are not embedded in the
server receipt. `secret_values_recorded` remains false by construction.

An exit code of zero means `EXECUTED`, not `VERIFIED`.

## Verification boundary

Independent verification remains a separate lifecycle step. For A6 that future
verification must establish at minimum:

- expected backup artifacts exist;
- PostgreSQL dump is readable with `pg_restore` listing;
- configuration/files archive is readable;
- systemd backup timer is active;
- Vikunja remains healthy.

## Deployment boundary

WB-0038E is repository-only. It does not create credentials, modify sshd or
Polkit on a target, deploy the subsystem, run A6 backups, mutate a VPS, or grant
production authority. Any deployment requires a separate target-bound plan,
fresh verification, and explicit authorization.
