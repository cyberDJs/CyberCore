# Governed Execution Bridge V1

Status: proposed implementation slice  
Work block: `WB-0037`

## Purpose

WB-0037 connects a bounded CyberCore action that has already passed continuity,
governance, and approval checks to an execution transport without creating a
general-purpose remote shell.

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

V1 therefore requests the dedicated `cybercore-exec` SSH subsystem using `ssh
-s`. The client sends one canonical JSON request on stdin. The future server-side
subsystem must parse that request and map the operation to its own fixed argv. It
must not evaluate request fields as shell text.

The subsystem is not deployed by this work block.

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

- `operation_id`;
- exact `target_id`;
- exact `plan_id` and `plan_revision`;
- `authorization_reference`;
- one supported operation.

The bridge does not mint or infer authorization. The authorization verifier that
precedes this bridge remains authoritative.

## Transport invariants

The local transport uses an argv vector and `subprocess.run(..., shell=False)`.
It requests an SSH subsystem rather than a remote command. Batch mode,
`IdentitiesOnly`, strict host-key checking, and a connection timeout are fixed in
the transport argv.

V1 deliberately does not support:

- arbitrary shell commands;
- `bash -c`, `sh -c`, or equivalent wrappers;
- caller-selected SSH hosts or users;
- command substitution or metacharacter interpretation;
- arbitrary sudo;
- arbitrary filesystem paths.

## Execution receipt

The receipt records only non-secret execution metadata:

- operation and target binding;
- plan/revision and authorization reference;
- exact local transport argv;
- start and completion timestamps;
- exit code;
- SHA-256 digests of stdout and stderr;
- whether mutation was possible.

Raw stdout/stderr are not embedded in the receipt. `secret_values_recorded` is
always false by construction.

An exit code of zero means `EXECUTED`, not `VERIFIED`.

## Verification boundary

Independent verification remains a separate lifecycle step. For A6 that future
verification must establish at minimum:

- expected backup artifacts exist;
- PostgreSQL dump is readable with `pg_restore` listing;
- configuration/files archive is readable;
- systemd backup timer is active;
- Vikunja remains healthy.

## Deferred

WB-0037 V1 does not deploy the server-side SSH subsystem, create credentials,
modify sshd, mutate the VPS, create backups, or expose a generic remote executor.
Those require a separate, target-bound deployment authorization.
