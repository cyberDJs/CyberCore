# Cloudflare DNS provider v0.1

Status: **implementation candidate / production writes gated**

CyberCore can discover a Cloudflare zone, snapshot DNS and DNSSEC state, calculate a deterministic diff for explicitly managed recordsets, and apply that exact diff only after a plan-bound operator approval.

## Safety contract

The provider is fail-closed:

1. DNS mutation is limited to recordsets explicitly listed in `managed_recordsets`.
2. Unmanaged DNS records are never deleted or rewritten.
3. A write requires both the exact current plan fingerprint and the exact approval string emitted by that plan.
4. The provider re-discovers state immediately before the write. Any drift changes the fingerprint and blocks execution.
5. All DNS writes are sent through Cloudflare's `/dns_records/batch` endpoint as one database transaction; network propagation of individual DNS keys is still not atomic.
6. Post-write discovery must converge to zero remaining changes.
7. API tokens are read only from the runtime secret alias `CLOUDFLARE_DNS_API_TOKEN`; token values are never written to manifests or receipts.
8. DNSSEC is read and reported in v0.1 but **DNSSEC mutation is intentionally out of scope**. Registrar DS changes remain a separate governed operation.
9. Supported record types in v0.1: `A`, `AAAA`, `CNAME`, `MX`, `TXT`.

## CLI

```text
cybercore cloudflare dns discover --zone example.cz
cybercore cloudflare dns plan --manifest .cybercore/providers/cloudflare/example.cz.yaml
cybercore cloudflare dns apply \
  --manifest .cybercore/providers/cloudflare/example.cz.yaml \
  --expected-plan <sha256> \
  --approve 'APPLY CLOUDFLARE DNS example.cz <sha256>'
```

`discover` and `plan` are read-only. `apply` is a production mutation boundary.

## Sarah Hair Design rollout

`sarahhairdesign.cz` is the first intended real target, but its desired-state manifest must not be guessed. The current public DNS is authoritative on WEDOS and currently exposes WEDOS MX records. Before Cloudflare cutover, the target manifest must be built from independently verified hosting and Seznam Email Profi records and then reviewed as one complete change set (web + mail + TXT + DNSSEC transition).
