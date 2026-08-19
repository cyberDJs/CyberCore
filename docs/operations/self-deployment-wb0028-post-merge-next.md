# WB-0028 Post-Merge Next Step

Date: 2026-08-19

## Next implementation after this PR

Add a `plan_only` deployment manifest validator.

It should:

- read the target registry;
- reject unresolved placeholders for live modes;
- reject secret-looking values;
- generate a non-secret plan receipt;
- never connect to InterServer.

## Later implementation

Add a manually triggered GitHub Actions dry-run workflow after the validator exists.