# Security Policy

## Secrets

Never commit:

- API keys
- SSH private keys
- passwords
- `.env` files
- database dumps
- private customer data
- private project data unless explicitly sanitized

## Immediate incident note

An InterServer API key was pasted into chat during bootstrap. Treat it as compromised.

Required action:

1. Revoke/delete the exposed key in InterServer.
2. Create a new key.
3. Store the new key only in a local secret manager or encrypted environment file.
4. Never paste the new key into chat or GitHub.

## Access model

- Prefer API tokens with minimum permissions.
- Prefer read-only access for discovery.
- Use separate keys for audit, deployment and administration.
- Use human approval for infrastructure-changing actions.
