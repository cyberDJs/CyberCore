# CyberCore #113 — inert SO_PEERCRED transport candidate

Status: isolated prototype only. This file is NOT a root broker daemon and provides no bind/listen/activation entrypoint, socket ACL, systemd unit, Polkit change, trusted root execution, credentials or backup transfer.

`nextcloud_r1_peercred_transport.py` accepts a *previously established* AF_UNIX stream socket; checks Linux kernel-provided SO_PEERCRED pid/uid/gid and rejects wrong peer UID. Its request decoder enforces a single bounded newline-terminated UTF-8 JSON frame with the six exact fields used by `Request` and rejects a caller-supplied peer uid. A dependency-injected callback receives only a validated request and kernel-observed uid; no command is selected or executed by this transport.

Tests use real socket.socketpair(AF_UNIX, SOCK_STREAM) and kernel SO_PEERCRED, plus synthetic payloads for wrong uid, injected uid field, malformed/multiple/oversized/missing-newline requests and non-Unix socket denial. They do not prove authorization or transfer; no root socket nor service is installed.

Important unimplemented protections: trusted root-owned socket binding and ownership/ACL; race-free preaccepted Unix stream lifecycle; acceptance loop limits/timeouts/resource exhaustion; actual SO_PEERCRED on the *deployed* socket; byte framing when multiple writes or frames arrive after a first newline; root-owned concrete FileBoundExecutionAuthorizationVerifier and exact runtime source approval; direct systemd denial; one-shot consume journal/real multiprocessing; strict parent path ownership; emergency rollback. Never use this candidate for privileged execution or assume CI PASS implies activation.

Related architecture ADR PR #181 and source-level Polkit bypass PR #180 are separate review artifacts; current main includes their merged code/doc versions, but no production authorization is implied.

Separate explicit approval, independent security review, full end-to-end negative tests, and a governed root installer/rollback are required before deployment. Do not activate SSH/systemd/Polkit or transfer backup.
