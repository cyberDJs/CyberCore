# WB-0028 Review Model

Date: 2026-08-19

## Review model for this slice

Because this PR is documentation/state-only and non-production:

- external human review is optional;
- manual AI review is required;
- CI and CodeQL are required;
- merge requires explicit Jan Kočí authorization.

## Stronger review required later

The following require stronger approval:

- executable staging workflow with remote write capability;
- secret alias setup;
- provider changes;
- production promotion;
- DNS/mail/billing/DirectAdmin/VPS changes;
- ADR acceptance.