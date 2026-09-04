from __future__ import annotations

from pathlib import Path

import pytest

from cybercore.cloudflare_dns import (
    CloudflareDnsError,
    DnsRecord,
    apply_manifest,
    build_plan,
    load_manifest,
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
    def __init__(self, records: tuple[DnsRecord, ...]) -> None:
        self.records = list(records)
        self.writes: list[tuple[str, str]] = []
        self._next = 10

    def find_zone(self, zone: str) -> tuple[str, str]:
        return "zone-1", "active"

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

    receipt = apply_manifest(
        api,
        manifest,
        expected_plan=plan.fingerprint,
        approval=plan.approval_text,
    )
    assert receipt["verified"] is True
    assert api.writes


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
