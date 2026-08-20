# Staging Remote-Write Gate Checklist v0

Date: 2026-08-20
Status: Draft checklist

## Purpose

Define the evidence required before any future CyberCore staging remote-write work can be authorized.

## Required before first staging remote write

- staging URL identified;
- staging filesystem path identified;
- production document root explicitly excluded;
- deployment method identified;
- staging-only identity confirmed;
- secret aliases defined without plaintext values;
- rollback method defined;
- effect verifier defined;
- no denied production/provider/DNS/mail/billing/DirectAdmin/VPS/WordPress/Nextcloud mutation;
- fresh explicit operator authorization for the remote-write work block.

## Evidence restrictions

Allowed evidence:

- aliases;
- scopes;
- owner/status fields;
- timestamps;
- safe fingerprints/hashes where appropriate;
- verification result labels.

Denied evidence:

- plaintext passwords;
- private keys;
- API tokens;
- TOTP seeds;
- recovery codes;
- reusable secrets.

## Stop line

If any target identity, rollback, effect verifier, secret alias, or authorization field is unknown, the work remains blocked.
