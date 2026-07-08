# Risk Register

Updated: 2026-07-08

| ID | Risk | Impact | Probability | Status | Mitigation |
|---|---|---:|---:|---|---|
| R-001 | API key exposed in chat | High | Confirmed | Open | Revoke immediately and create new key |
| R-002 | Production and development are the same environment | High | High | Open | Add staging-lite workflow and rollback |
| R-003 | FTP-first deployment | Medium | High | Open | Move to Git/rsync/GitHub Actions hybrid |
| R-004 | Incomplete inventory | Medium | High | Open | Build inventory via APIs and read-only audit |
| R-005 | Unknown backup recoverability | High | Medium | Open | Define and test restore |
| R-006 | Softaculous apps may increase attack surface | Medium | Medium | Open | Classify keep/evaluate/remove |
