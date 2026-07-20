# CXP Artifact Specification v1

Status: **Draft for implementation**  
Identifier: **CXP/1**  
Scope: immutable CyberCore artifacts used by Publisher, Runtime, Registry and transports.

## 1. Purpose

CXP is the canonical artifact format for delivering CyberCore Work Blocks.

A CXP artifact must be:

- immutable;
- content-addressed;
- reproducible;
- independently verifiable;
- transport-independent;
- optionally signed;
- optionally encrypted.

CXP defines the artifact contract. A transport such as Google Drive, local
filesystem, S3 or GitHub Releases only moves bytes and is not trusted with
artifact integrity or confidentiality.

## 2. File extension and media type

Recommended extension:

```text
.cxp
```

Media type:

```text
application/vnd.cybercore.cxp+tar
```

A `.cxp` file is a deterministic POSIX tar archive. Compression is external to
the logical format and MUST be declared in metadata. CXP/1 reference
implementations SHOULD use Zstandard when compression is enabled.

## 3. Canonical layout

```text
artifact.cxp
├── manifest.json
├── metadata.json
├── checksums.sha256
├── payload.tar.zst
├── signature.ed25519      optional
└── envelope.json          optional
```

Unknown top-level entries MUST be rejected unless a future compatible profile
explicitly permits them.

## 4. Manifest

`manifest.json` is the normative machine-readable contract.

Required fields:

- `schema`
- `artifact_id`
- `version`
- `created_at`
- `publisher`
- `payload`
- `compatibility`
- `risk`

Example:

```json
{
  "schema": "cxp/v1",
  "artifact_id": "WB-0009-cxp-artifact-spec-v1",
  "version": "1.0.0",
  "created_at": "2026-07-16T09:00:00Z",
  "publisher": {
    "id": "cyberdjs",
    "name": "CyberDJS"
  },
  "payload": {
    "file": "payload.tar.zst",
    "media_type": "application/vnd.cybercore.payload+tar",
    "compression": "zstd",
    "digest": {
      "algorithm": "sha256",
      "value": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
  },
  "compatibility": {
    "runtime": ">=0.1.0,<0.2.0"
  },
  "risk": "low"
}
```

## 5. Metadata

`metadata.json` contains non-security-critical operational context.

Typical fields:

- title;
- description;
- tags;
- estimated apply time;
- rollback support;
- restart requirement;
- affected components;
- human notes.

Runtime MUST NOT use metadata as the sole basis for trust decisions.

## 6. Checksums

`checksums.sha256` contains SHA-256 digests for every top-level entry except
itself and any outer encrypted envelope.

Format:

```text
<lowercase hex digest><two spaces><relative POSIX path>
```

Rules:

- paths MUST be relative;
- absolute paths are forbidden;
- `..` segments are forbidden;
- duplicate paths are forbidden;
- paths are UTF-8;
- entries are sorted lexicographically;
- line endings are LF;
- the file ends with a newline.

## 7. Artifact identity

The canonical artifact digest is:

```text
sha256(canonical .cxp bytes)
```

The digest, not the filename, is the artifact identity.

Recommended URI:

```text
cxp:sha256:<64 lowercase hex characters>
```

A registry MAY associate human-readable aliases with a digest. Aliases are
mutable; artifact digests are not.

## 8. Deterministic build rules

To produce reproducible bytes:

- tar paths are sorted lexicographically;
- uid and gid are `0`;
- uname and gname are empty;
- mtime is `0`;
- file mode is normalized;
- no symlinks, hardlinks, devices or FIFOs;
- JSON is UTF-8, LF, sorted keys and no insignificant whitespace;
- payload archive follows the same normalization rules.

Two builds from identical inputs MUST produce identical artifact digests.

## 9. Signature

When present, `signature.ed25519` signs the canonical SHA-256 digest of the CXP
artifact profile without the signature entry itself.

The signature proves origin and integrity. It does not provide confidentiality.

Trust policy is local. Runtime MUST distinguish:

- cryptographically valid signature;
- trusted publisher;
- untrusted or unknown publisher.

## 10. Encryption

Encryption is a transport envelope, not a change to CXP semantics.

Recommended encrypted representation:

```text
artifact.cxp.age
```

The plaintext is the complete canonical `.cxp` artifact. Age/X25519 is the
reference encryption mechanism.

The transport can see ciphertext size and timing, but not manifest, metadata or
payload content.

## 11. Verification order

Runtime MUST verify in this order:

```text
transport object
-> decrypt envelope when present
-> calculate artifact digest
-> validate archive layout
-> validate JSON schemas
-> verify checksums
-> verify signature when present
-> evaluate local trust policy
-> evaluate compatibility
-> evaluate risk and approval policy
-> expose artifact as READY
```

No apply action may run before all mandatory gates pass.

## 12. Compatibility

CXP follows semantic versioning for the format specification.

- unknown major version: reject;
- newer minor version: accept only if all required features are understood;
- patch changes: clarification or bug fix without format breakage.

Runtime compatibility constraints use PEP 440 syntax in CXP/1.

## 13. Security requirements

CXP/1 forbids:

- path traversal;
- absolute paths;
- symlinks and hardlinks;
- executable content outside the declared payload;
- duplicate archive paths;
- undeclared top-level files;
- unchecked extraction;
- secrets in logs;
- trust based only on transport location.

Extraction MUST occur into a new private directory with restrictive
permissions.

## 14. Lifecycle

```text
SOURCE
-> BUILT
-> VERIFIED
-> SIGNED        optional
-> ENCRYPTED     optional
-> PUBLISHED
-> RECEIVED
-> READY
-> APPLIED
-> ARCHIVED
```

Artifact bytes are immutable after `BUILT`. Any modification creates a new
artifact digest.

## 15. Reference files

- `schemas/cxp-manifest-v1.schema.json`
- `schemas/cxp-metadata-v1.schema.json`
- `examples/cxp/manifest.valid.json`
- `examples/cxp/metadata.valid.json`

## 16. Deferred from CXP/1

- transparency logs;
- threshold and multi-party signatures;
- delta artifacts;
- remote payload references;
- OCI registry mapping;
- hardware-backed key requirements;
- policy language beyond local Runtime configuration.
