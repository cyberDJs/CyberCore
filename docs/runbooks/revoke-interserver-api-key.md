# Runbook: Revoke InterServer API Key

Updated: 2026-07-08

## Goal

Remove an exposed InterServer API key and replace it with a new one stored safely.

## Steps

1. Open InterServer account settings.
2. Go to API Access Tokens / API Access.
3. Revoke/delete the exposed key.
4. Create a new key.
5. Copy it once.
6. Store it in a local secret manager or encrypted local `.env`.
7. Do not paste it into chat.
8. Do not commit it to GitHub.

## Verification

- Old key no longer works.
- New key is stored outside the repository.
- Repository contains no secrets.
