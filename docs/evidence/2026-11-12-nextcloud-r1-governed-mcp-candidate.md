# CodeChangeEvidence — Nextcloud R1 governed MCP transfer candidate

- change_id: CC-NC-R1-GOVERNED-MCP-20261112
- project: cyberDJs/CyberCore
- base_identity: main@ae2f4572df74bf2cc49228ce88aab1f9b0e5fb42
- requirement_or_problem: issue #113 cannot complete full off-host archive proof without a safe non-manual transfer capability
- purpose: add a fail-closed, identity-bound MCP-to-governed-execution candidate without creating a general shell
- beneficiary: CyberCore operator and Nextcloud recovery workflow
- before_behavior: Room MCP has no execution capability; governed SSH bridge has only the tasks/Vikunja target
- after_behavior: repository candidate supports a fixed CyberSkills target and conditional Johnny Work Nextcloud R1 transfer/status/verify tool
- design: fixed target/path operation family; async static systemd transfer; dedicated restricted credential outside repo; strict SSH settings; exact authorization binding; non-secret receipts
- alternatives: generic shell, production-key reuse and laptop relay rejected
- expected_improvement: removes recurring manual shell/key choreography while preserving least privilege and auditability
- risks_tradeoffs: second execution target, longer verifier budget, deployment requires separate credential provisioning, trusted approval-manifest provisioning and dedicated Johnny Work Unix identity/socket ACL
- security_impact: authority surface remains allowlisted; raw secrets/commands/paths are not caller controlled; mutation requires short-lived exact approval manifests on both client and server
- rollback: revoke dedicated source key, remove target credential, policy/unit/subsystem/helper and MCP handler; preserve backup evidence
- deployment: NOT AUTHORIZED
- merge: NOT AUTHORIZED
- production_restore: NOT AUTHORIZED
- independent_verification: pending exact-HEAD CI/CodeQL and review
- effect_verification: runtime effect intentionally not claimed because no deployment occurs

- security_followup: transfer now requires independently observed source SHA-256 evidence before it can atomically publish the off-host archive
- identity_followup: mutating MCP enablement is deployment-blocked until Johnny Work frontend isolation is proven against same-uid cross-socket access, with separate Unix identities as the fallback

- identity_hardening: governed Johnny Work socket now requires a dedicated non-root Unix peer UID distinct from the broker UID and rejects mismatched peers before request parsing
- deployment_acl_gate: deployment must grant only the dedicated Johnny Work UID the minimum socket ACL required for connection; repository candidate does not mutate OS users or ACLs

- approval_hardening: added root-owned file-bound exact approval verifier; raw approval is represented only by SHA-256, exact tuple binding and <=1h UTC validity
- server_authority_scope: cyberskills-vps selects the file-bound verifier; existing tasks.cyberdjs.org remains deny-all
- live_authority: NOT PRESENT; repository contains no production approval manifest
