# WB-0028 Risk Pre-Mortem

Date: 2026-08-19
Work block: `WB-0028`
Scope: staging self-deployment foundation

## Main failure modes

### 1. Staging is accidentally production

Risk: the deploy target points to a production document root or production domain.

Mitigation:

- target registry must mark production mutation as denied;
- staging URL/path must be verified before remote write;
- first remote write requires explicit operator authorization.

### 2. Production credentials are reused

Risk: staging deploy uses production credentials and broadens blast radius.

Mitigation:

- no production credentials allowed for staging;
- deploy identity must be staging-path-only;
- secrets are aliases only in GitHub/docs.

### 3. No rollback on shared hosting

Risk: shared hosting lacks atomic symlink deployment or snapshot restore.

Mitigation:

- prefer immutable release directories;
- fallback to timestamped backup or no-overwrite upload;
- block nontrivial remote write if rollback is unknown.

### 4. Execution receipt is mistaken for verification

Risk: upload success is treated as working staging.

Mitigation:

- effect verifier is mandatory;
- receipt must include verifier result;
- deployment success without effect verification remains `UNVERIFIED`.

### 5. Scope creeps into production automation

Risk: staging pipeline becomes production deployment without governance.

Mitigation:

- ADR candidate explicitly blocks production promotion;
- production requires separate MOP and approval;
- PR scope remains docs/state only for this slice.

## Result

The current slice is safe to implement as documentation/state/target-contract scaffolding. Live staging deployment remains blocked.