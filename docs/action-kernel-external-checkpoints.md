# Action Kernel external audit checkpoint contract (WB-AK-010)

Tracks #127. This is **local verification plumbing**, not a deployed trusted
anchor service.

A checkpoint contains `database_identity`, `sequence`, and `event_hash`.
It becomes an anchor **only after an independent authority durably retains it
outside the SQLite database and its writable security domain**. Verifying
against a trusted retained checkpoint detects truncating or rewriting its
anchored prefix. Events after the anchored sequence are not protected by that
checkpoint. A fake caller-supplied checkpoint offers no protection.

Implementation is currently a non-atomic snapshot/check across separately
opened SQLite connections. Writers may append during reads; for concurrent
production operation replace this with a transactionally consistent read-only
snapshot and independently anchored identity, sequence and digest.

Do not use a working-directory JSON file, Git commit in the same compromised
authority, or an automatically editable local checkpoint as proof of immutable
storage. An independently authenticated and access-controlled endpoint or
separately held signed checkpoint is necessary. Production deployment,
credentials, cloud systems and remote actions are excluded.

Rollback: stop using this optional module; preserve all audit and checkpoint
data. Never delete existing evidence to force a clean verification.
