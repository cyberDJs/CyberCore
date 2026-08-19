# Self-Deployment Glossary v0

Date: 2026-08-19
Work block: `WB-0028`

## Terms

### Self-development

CyberCore's ability to propose, implement, test, and prepare its own changes through branch and PR workflow.

### Self-deployment

CyberCore's ability to deploy an approved artifact to a non-production target, verify the effect, and record evidence.

### Staging apply

A remote write to the staging target. It is not production promotion.

### Effect verification

Independent check that the intended staging effect actually happened.

### Receipt

Non-secret evidence object recording a deployment plan, dry run, or staging apply outcome.

### Target registry

Non-secret metadata describing a deployment target and its safety gates.

### Secret alias

A reference name for a secret stored in an approved secret system. It is not the secret value.