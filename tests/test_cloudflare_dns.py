from __future__ import annotations

import json
from pathlib import Path

import pytest

from cybercore.cloudflare_dns import (
    CloudflareClient,
    CloudflareDnsError,
    DnsChange,
    DnsManifest,
    DnsRecord,
    apply_manifest,
    build_plan,
    load_manifest,
    plan_from_manifest,
)


MANIFEST = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: "@"
  - type: MX
    name: "@"
  - type: TXT
    name: "@"
records:
  - type: A
    name: "@"
    content: 192.0.2.10
    ttl: 300
    proxied: false
  - type: MX
    name: "@"
    content: mx.example.net
    priority: 10
    ttl: 300
  - type: TXT
    name: "@"
    content: v=spf1 include:example.net -all
    ttl: 300
"""


def _manifest(tmp_path: Path):
    path = tmp_path / "dns.yaml"
    path.write_text(MANIFEST, encoding="utf-8")
    return load_manifest(path)


def test_manifest_normalizes_apex_and_rejects_proxy_on_mx(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    assert manifest.zone == "example.cz"
    assert manifest.records[0].name == "example.cz"

    path = tmp_path / "bad.yaml"
    path.write_text(
        MANIFEST.replace("priority: 10", "priority: 10\n    proxied: true"), encoding="utf-8"
    )
    with pytest.raises(CloudflareDnsError, match="forbids proxied=true for MX"):
        load_manifest(path)


def test_manifest_rejects_duplicate_yaml_keys_and_aliases(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        MANIFEST.replace("zone: example.cz", "zone: example.cz\nzone: evil.cz"), encoding="utf-8"
    )
    with pytest.raises(CloudflareDnsError, match="duplicate key: zone"):
        load_manifest(duplicate)

    alias = tmp_path / "alias.yaml"
    alias.write_text(
        MANIFEST.replace("content: 192.0.2.10", "content: &target 192.0.2.10").replace(
            "content: mx.example.net", "content: *target"
        ),
        encoding="utf-8",
    )
    with pytest.raises(CloudflareDnsError, match="forbids YAML"):
        load_manifest(alias)


def test_plan_is_minimal_and_fingerprinted(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    current = (
        DnsRecord("A", "example.cz", "192.0.2.9", 300, False, None, "a1"),
        DnsRecord("MX", "example.cz", "old.example.net", 300, False, 10, "mx1"),
        DnsRecord("TXT", "example.cz", "v=spf1 include:example.net -all", 300, False, None, "txt1"),
        DnsRecord("TXT", "unmanaged.example.cz", "leave-me", 300, False, None, "txt2"),
    )
    plan = build_plan(manifest, zone_id="zone-1", current_records=current)
    assert [change.action for change in plan.changes] == ["UPDATE", "UPDATE"]
    assert len(plan.fingerprint) == 64
    assert plan.approval_text.startswith("APPLY CLOUDFLARE DNS example.cz ")


class FakeApi:
    def __init__(self, records: tuple[DnsRecord, ...], *, status: str = "active") -> None:
        self.records = list(records)
        self.status = status
        self.writes: list[tuple[str, str]] = []
        self._next = 10

    def find_zone(self, zone: str) -> tuple[str, str]:
        return "zone-1", self.status

    def list_dns_records(self, zone_id: str) -> tuple[DnsRecord, ...]:
        return tuple(self.records)

    def get_dnssec(self, zone_id: str) -> dict[str, object]:
        return {"status": "active"}

    def apply_dns_batch(self, zone_id: str, changes) -> None:
        for change in changes:
            if change.action == "CREATE":
                assert change.after is not None
                self._next += 1
                record = change.after
                self.records.append(DnsRecord(**{**record.__dict__, "record_id": f"r{self._next}"}))
                self.writes.append(("CREATE", record.name))
            elif change.action == "UPDATE":
                assert change.before is not None and change.after is not None
                assert change.before.record_id is not None
                record_id = change.before.record_id
                record = change.after
                self.records = [
                    DnsRecord(**{**record.__dict__, "record_id": record_id})
                    if item.record_id == record_id
                    else item
                    for item in self.records
                ]
                self.writes.append(("UPDATE", record.name))
            elif change.action == "DELETE":
                assert change.before is not None and change.before.record_id is not None
                record_id = change.before.record_id
                target = next(item for item in self.records if item.record_id == record_id)
                self.records = [item for item in self.records if item.record_id != record_id]
                self.writes.append(("DELETE", target.name))


def test_apply_is_blocked_without_exact_plan_bound_approval(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    api = FakeApi((DnsRecord("A", "example.cz", "192.0.2.9", 300, False, None, "a1"),))
    plan = build_plan(manifest, zone_id="zone-1", current_records=api.list_dns_records("zone-1"))

    with pytest.raises(CloudflareDnsError, match="requires exact approval"):
        apply_manifest(api, manifest, expected_plan=plan.fingerprint, approval="yes")
    assert api.writes == []

    evidence_dir = tmp_path / "evidence"
    receipt = apply_manifest(
        api,
        manifest,
        expected_plan=plan.fingerprint,
        approval=plan.approval_text,
        evidence_dir=evidence_dir,
    )
    assert receipt["verified"] is True
    assert api.writes
    assert (evidence_dir / "pre-write-zone-snapshot.json").is_file()
    assert (evidence_dir / "rollback-manifest.yaml").is_file()
    assert (evidence_dir / "rollback-prepared-receipt.json").is_file()
    assert (evidence_dir / "post-write-zone-snapshot.json").is_file()
    assert (evidence_dir / "apply-receipt.json").is_file()
    rollback = load_manifest(evidence_dir / "rollback-manifest.yaml")
    assert any(record.content == "192.0.2.9" for record in rollback.records)


def test_apply_rejects_drift_before_any_write(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    api = FakeApi((DnsRecord("A", "example.cz", "192.0.2.9", 300, False, None, "a1"),))
    plan = build_plan(manifest, zone_id="zone-1", current_records=api.list_dns_records("zone-1"))
    api.records.append(
        DnsRecord("MX", "example.cz", "drift.example.net", 300, False, 5, "mx-drift")
    )

    with pytest.raises(CloudflareDnsError, match="plan drifted"):
        apply_manifest(
            api,
            manifest,
            expected_plan=plan.fingerprint,
            approval=plan.approval_text,
        )
    assert api.writes == []


def _load_inline_manifest(tmp_path: Path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return load_manifest(path)


def test_manifest_rejects_multiple_cnames_at_one_name(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: CNAME
    name: www
records:
  - type: CNAME
    name: www
    content: one.example.net
  - type: CNAME
    name: www
    content: two.example.net
"""
    with pytest.raises(CloudflareDnsError, match="at most one desired CNAME"):
        _load_inline_manifest(tmp_path, "multi-cname.yaml", content)


def test_manifest_rejects_non_auto_ttl_for_proxied_record(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: www
records:
  - type: A
    name: www
    content: 192.0.2.10
    proxied: true
    ttl: 300
"""
    with pytest.raises(CloudflareDnsError, match="require ttl: 1"):
        _load_inline_manifest(tmp_path, "proxied-ttl.yaml", content)


def test_manifest_rejects_mixed_proxy_mode_for_address_records(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: www
records:
"""
    content += """\
  - type: A
    name: www
    content: 192.0.2.10
    proxied: true
    ttl: 1
  - type: A
    name: www
    content: 192.0.2.11
    proxied: false
    ttl: 300
"""
    with pytest.raises(CloudflareDnsError, match="one consistent Cloudflare proxy mode"):
        _load_inline_manifest(tmp_path, "mixed-proxy.yaml", content)


def test_plan_blocks_unmanaged_a_before_creating_cname(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: CNAME
    name: www
records:
  - type: CNAME
    name: www
    content: target.example.net
"""
    manifest = _load_inline_manifest(tmp_path, "cname.yaml", content)
    current = (DnsRecord("A", "www.example.cz", "192.0.2.9", 300, False, None, "a1"),)
    with pytest.raises(CloudflareDnsError, match="conflicts with unmanaged A"):
        build_plan(manifest, zone_id="zone-1", current_records=current)


def test_plan_allows_managed_a_replacement_with_cname(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: www
  - type: CNAME
    name: www
records:
  - type: CNAME
    name: www
    content: target.example.net
"""
    manifest = _load_inline_manifest(tmp_path, "managed-replacement.yaml", content)
    current = (DnsRecord("A", "www.example.cz", "192.0.2.9", 300, False, None, "a1"),)
    plan = build_plan(manifest, zone_id="zone-1", current_records=current)
    assert [change.action for change in plan.changes] == ["DELETE", "CREATE"]


def test_plan_blocks_unmanaged_ns_at_desired_owner_name(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: delegated
records:
  - type: A
    name: delegated
    content: 192.0.2.10
"""
    manifest = _load_inline_manifest(tmp_path, "ns-conflict.yaml", content)
    current = (DnsRecord("NS", "delegated.example.cz", "ns1.example.net", 300, False, None, "ns1"),)
    with pytest.raises(CloudflareDnsError, match="unmanaged NS"):
        build_plan(manifest, zone_id="zone-1", current_records=current)


def test_apply_requires_new_evidence_directory_before_write(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    api = FakeApi((DnsRecord("A", "example.cz", "192.0.2.9", 300, False, None, "a1"),))
    plan = build_plan(manifest, zone_id="zone-1", current_records=api.list_dns_records("zone-1"))
    with pytest.raises(CloudflareDnsError, match="requires a new evidence directory"):
        apply_manifest(
            api,
            manifest,
            expected_plan=plan.fingerprint,
            approval=plan.approval_text,
        )
    assert api.writes == []

    evidence_dir = tmp_path / "already-exists"
    evidence_dir.mkdir()
    with pytest.raises(CloudflareDnsError, match="must be a new writable path"):
        apply_manifest(
            api,
            manifest,
            expected_plan=plan.fingerprint,
            approval=plan.approval_text,
            evidence_dir=evidence_dir,
        )
    assert api.writes == []


def test_plan_blocks_proxy_mode_change_to_unmanaged_address_record(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
managed_recordsets:
  - type: A
    name: www
records:
  - type: A
    name: www
    content: 192.0.2.10
    proxied: true
    ttl: 1
"""
    manifest = _load_inline_manifest(tmp_path, "proxy-conflict.yaml", content)
    current = (DnsRecord("AAAA", "www.example.cz", "2001:db8::1", 300, False, None, "aaaa1"),)
    with pytest.raises(CloudflareDnsError, match="proxy mode.*unmanaged A/AAAA"):
        build_plan(manifest, zone_id="zone-1", current_records=current)


def test_template_manifest_cannot_be_applied(tmp_path: Path) -> None:
    content = """\
version: cybercore.cloudflare-dns/v0.1
zone: example.cz
template: true
managed_recordsets:
  - type: A
    name: "@"
records: []
"""
    manifest = _load_inline_manifest(tmp_path, "template.yaml", content)
    api = FakeApi(())
    with pytest.raises(CloudflareDnsError, match="template Cloudflare DNS manifest"):
        apply_manifest(
            api,
            manifest,
            expected_plan="unused",
            approval="unused",
            evidence_dir=tmp_path / "unused-evidence",
        )
    assert api.writes == []


def test_client_uses_patch_for_updates_to_preserve_unmodeled_metadata() -> None:
    captured: dict[str, object] = {}

    def requester(request):
        captured["method"] = request.method
        captured["body"] = request.data
        return 200, b'{"success":true,"result":{}}'

    client = CloudflareClient("test-token", requester=requester)
    before = DnsRecord("A", "www.example.cz", "192.0.2.9", 300, False, None, "a1")
    after = DnsRecord("A", "www.example.cz", "192.0.2.10", 300, False)
    change = DnsChange("UPDATE", ("A", "www.example.cz"), before, after)

    client.apply_dns_batch("zone-1", (change,))
    assert captured["method"] == "POST"
    raw = captured["body"]
    assert isinstance(raw, bytes)
    payload = json.loads(raw)
    assert payload["puts"] == []
    assert payload["patches"] == [{"id": "a1", **after.api_payload()}]


def test_pending_zone_can_be_planned_before_nameserver_cutover(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    pending = FakeApi((), status="pending")
    plan = plan_from_manifest(pending, manifest)
    assert plan.changes

    moved = FakeApi((), status="moved")
    with pytest.raises(CloudflareDnsError, match="not safe for DNS planning or mutation"):
        plan_from_manifest(moved, manifest)


def test_find_zone_does_not_filter_out_pending_zone() -> None:
    captured: dict[str, str] = {}

    def requester(request):
        captured["url"] = request.full_url
        return (
            200,
            b'{"success":true,"result":[{"id":"zone-1","name":"example.cz","status":"pending"}]}',
        )

    client = CloudflareClient("test-token", requester=requester)
    assert client.find_zone("example.cz") == ("zone-1", "pending")
    assert "status=" not in captured["url"]


def test_plan_rejects_more_than_free_tier_batch_limit() -> None:
    records = tuple(
        DnsRecord("A", "example.cz", f"192.0.2.{index}", 300, False) for index in range(1, 202)
    )
    manifest = DnsManifest(
        zone="example.cz",
        managed_recordsets=(("A", "example.cz"),),
        records=records,
        template=False,
    )
    with pytest.raises(CloudflareDnsError, match="limits one plan to 200 changes"):
        build_plan(manifest, zone_id="zone-1", current_records=())
