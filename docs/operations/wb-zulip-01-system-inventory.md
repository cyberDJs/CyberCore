# WB-ZULIP-01 — bounded system inventory

Status: repository candidate only; not deployed

## Goal

Add one read-only CyberCore execution operation, `system.inventory`, to collect the minimum host-capacity evidence required to size a future Zulip deployment on the existing `tasks.cyberdjs.org` VPS.

## Boundary

The operation:

- is bound to the existing canonical target `tasks.cyberdjs.org`;
- accepts no arguments;
- does not open a shell;
- does not accept caller-selected paths, commands, users, hosts, or Docker options;
- runs as the existing `cybercore-exec` identity;
- does not add that identity to the Docker group and does not add sudo or Polkit privilege;
- exposes only a schema-validated structured result for this one operation;
- leaves stdout for all other operations digest-only.

The structured result contains only:

- logical CPU count and 1/5/15 minute load;
- total/available RAM and swap;
- root-filesystem total/used/free bytes;
- Docker CLI/server availability;
- bounded container name/image/status/ports/size rows when Docker access is already available;
- bounded Docker storage summary rows.

No environment variables, file contents, process command lines, credentials, mounts, labels, container environment, Docker inspect output, account data, or secret values are collected.

## Docker privilege rule

Docker discovery is best-effort. If the existing service identity cannot access the Docker daemon, the result reports `denied_or_unreachable`. If the daemon is reachable but a later bounded Docker subcommand fails, times out, or emits malformed JSON rows, the result reports `partial_failure` rather than silently treating missing data as an empty successful result. This work block must not make Docker readable by adding `cybercore-exec` to the `docker` group because Docker daemon access is effectively root-equivalent on a normal host.

## Result-disclosure rule

The existing execution bridge stores raw stdout only transiently and records hashes in normal receipts. `system.inventory` is the only operation in this work block permitted to promote command output into a returned `result`, and only after exact schema validation on both the server and client side.

Malformed, extra-field, unbound, or non-JSON inventory output fails closed and is not promoted as inventory evidence.

## Deployment boundary

This repository change does not install the helper on the VPS, reload SSH, change privileges, resize the VPS, deploy Zulip, change DNS, or create secrets.

A future deployment requires a target-bound deployment packet and separate explicit authorization.

## Verification

Required before merge readiness:

1. unit/contract tests;
2. exact-head CI;
3. exact-head CodeQL;
4. fresh independent review;
5. no unresolved P1/P2 security or privilege-boundary finding.

Runtime effect verification is impossible until a later authorized deployment installs the updated server artifact.


## Upgrade ordering and timeout budget

Bootstrap installs the inventory helper, operations map, protocol, and authorization dependency before replacing the dispatcher so an interrupted upgrade cannot leave the dispatcher importing a not-yet-installed module. The inventory operation receives a 20-second server budget, which exceeds the aggregate 15-second Docker probe budget plus Python and local collection overhead.


## Numeric validation

Load-average values are accepted only when they are finite real numbers. `NaN`, positive/negative infinity, and values that overflow Python float conversion fail closed as validation errors and are never promoted into capacity evidence.
