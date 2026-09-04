from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml
from yaml.nodes import MappingNode, Node, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, DirectiveToken

API_BASE = "https://api.cloudflare.com/client/v4"
TOKEN_ENV = "CLOUDFLARE_DNS_API_TOKEN"
SUPPORTED_TYPES = {"A", "AAAA", "CNAME", "MX", "TXT"}
PROXY_CAPABLE_TYPES = {"A", "AAAA", "CNAME"}


class CloudflareDnsError(RuntimeError):
    """Fail-closed Cloudflare DNS provider error."""


@dataclass(frozen=True)
class DnsRecord:
    record_type: str
    name: str
    content: str
    ttl: int = 1
    proxied: bool = False
    priority: int | None = None
    record_id: str | None = None

    def recordset(self) -> tuple[str, str]:
        return (self.record_type, self.name)

    def semantic_key(self) -> tuple[object, ...]:
        return (
            self.record_type,
            self.name,
            self.content,
            self.ttl,
            self.proxied,
            self.priority,
        )

    def api_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "type": self.record_type,
            "name": self.name,
            "content": self.content,
            "ttl": self.ttl,
        }
        if self.record_type in PROXY_CAPABLE_TYPES:
            payload["proxied"] = self.proxied
        if self.priority is not None:
            payload["priority"] = self.priority
        return payload

    def public_dict(self) -> dict[str, object]:
        result = self.api_payload()
        if self.record_id is not None:
            result["id"] = self.record_id
        return result


@dataclass(frozen=True)
class DnsChange:
    action: str
    recordset: tuple[str, str]
    before: DnsRecord | None
    after: DnsRecord | None

    def public_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "recordset": {"type": self.recordset[0], "name": self.recordset[1]},
            "before": None if self.before is None else self.before.public_dict(),
            "after": None if self.after is None else self.after.public_dict(),
        }


@dataclass(frozen=True)
class DnsManifest:
    zone: str
    managed_recordsets: tuple[tuple[str, str], ...]
    records: tuple[DnsRecord, ...]


@dataclass(frozen=True)
class DnsPlan:
    zone: str
    zone_id: str
    changes: tuple[DnsChange, ...]
    fingerprint: str

    @property
    def approval_text(self) -> str:
        return f"APPLY CLOUDFLARE DNS {self.zone} {self.fingerprint}"

    def public_dict(self) -> dict[str, object]:
        return {
            "zone": self.zone,
            "zone_id": self.zone_id,
            "fingerprint": self.fingerprint,
            "approval_text": self.approval_text,
            "change_count": len(self.changes),
            "changes": [change.public_dict() for change in self.changes],
        }


class CloudflareApi(Protocol):
    def find_zone(self, zone: str) -> tuple[str, str]: ...

    def list_dns_records(self, zone_id: str) -> tuple[DnsRecord, ...]: ...

    def get_dnssec(self, zone_id: str) -> dict[str, object]: ...

    def apply_dns_batch(self, zone_id: str, changes: tuple[DnsChange, ...]) -> None: ...


Requester = Callable[[Request], tuple[int, bytes]]


def _default_requester(request: Request) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed Cloudflare API origin
            return response.status, response.read()
    except HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return exc.code, body
    except (URLError, OSError) as exc:
        raise CloudflareDnsError("Cloudflare API request failed") from exc


class CloudflareClient:
    def __init__(self, token: str, *, requester: Requester = _default_requester) -> None:
        token = token.strip()
        if not token:
            raise CloudflareDnsError("Cloudflare API token is empty")
        self._token = token
        self._requester = requester

    @classmethod
    def from_environment(cls) -> "CloudflareClient":
        token = os.environ.get(TOKEN_ENV, "")
        if not token:
            raise CloudflareDnsError(
                f"required secret alias {TOKEN_ENV} is unavailable; secret value was not read"
            )
        return cls(token)

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
    ) -> object:
        url = f"{API_BASE}{path}"
        if query:
            url += "?" + urlencode({key: str(value) for key, value in query.items()})
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        status, raw = self._requester(request)
        try:
            decoded = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudflareDnsError("Cloudflare API returned an invalid response") from exc
        if (
            status < 200
            or status >= 300
            or not isinstance(decoded, dict)
            or not decoded.get("success")
        ):
            raise CloudflareDnsError(f"Cloudflare API request failed with HTTP {status}")
        return decoded.get("result")

    def find_zone(self, zone: str) -> tuple[str, str]:
        result = self._request(
            "GET", "/zones", query={"name": zone, "status": "active", "per_page": 50}
        )
        if not isinstance(result, list):
            raise CloudflareDnsError("Cloudflare zones response is invalid")
        exact = [item for item in result if isinstance(item, dict) and item.get("name") == zone]
        if len(exact) != 1:
            raise CloudflareDnsError(f"expected exactly one active Cloudflare zone for {zone}")
        zone_id = exact[0].get("id")
        status = exact[0].get("status")
        if not isinstance(zone_id, str) or not zone_id or not isinstance(status, str):
            raise CloudflareDnsError("Cloudflare zone identity is invalid")
        return zone_id, status

    def list_dns_records(self, zone_id: str) -> tuple[DnsRecord, ...]:
        records: list[DnsRecord] = []
        page = 1
        while True:
            result = self._request(
                "GET",
                f"/zones/{zone_id}/dns_records",
                query={"per_page": 500, "page": page},
            )
            if not isinstance(result, list):
                raise CloudflareDnsError("Cloudflare DNS records response is invalid")
            for item in result:
                self._append_api_record(records, item)
            if len(result) < 500:
                break
            page += 1
            if page > 1000:
                raise CloudflareDnsError("Cloudflare DNS pagination exceeded the safety limit")
        return tuple(records)

    @staticmethod
    def _append_api_record(records: list[DnsRecord], item: object) -> None:
        if not isinstance(item, dict):
            raise CloudflareDnsError("Cloudflare DNS record is invalid")
        record_type = item.get("type")
        name = item.get("name")
        content = item.get("content")
        ttl = item.get("ttl", 1)
        record_id = item.get("id")
        if (
            not isinstance(record_type, str)
            or not isinstance(name, str)
            or not isinstance(content, str)
            or not isinstance(record_id, str)
        ):
            raise CloudflareDnsError("Cloudflare DNS record identity is invalid")
        if not isinstance(ttl, int):
            raise CloudflareDnsError("Cloudflare DNS record TTL is invalid")
        priority = item.get("priority")
        if priority is not None and not isinstance(priority, int):
            raise CloudflareDnsError("Cloudflare DNS record priority is invalid")
        records.append(
            DnsRecord(
                record_type=record_type,
                name=name.rstrip("."),
                content=content,
                ttl=ttl,
                proxied=bool(item.get("proxied", False)),
                priority=priority,
                record_id=record_id,
            )
        )

    def get_dnssec(self, zone_id: str) -> dict[str, object]:
        result = self._request("GET", f"/zones/{zone_id}/dnssec")
        if not isinstance(result, dict):
            raise CloudflareDnsError("Cloudflare DNSSEC response is invalid")
        allowed = {"status", "flags", "algorithm", "key_type", "digest_type", "digest", "ds"}
        return {key: value for key, value in result.items() if key in allowed}

    def apply_dns_batch(self, zone_id: str, changes: tuple[DnsChange, ...]) -> None:
        if len(changes) > 200:
            raise CloudflareDnsError("Cloudflare DNS v0.1 limits one batch to 200 changes")
        deletes: list[dict[str, object]] = []
        puts: list[dict[str, object]] = []
        posts: list[dict[str, object]] = []
        for change in changes:
            if change.action == "DELETE" and change.before is not None:
                if not change.before.record_id:
                    raise CloudflareDnsError(
                        "cannot delete Cloudflare DNS record without record id"
                    )
                deletes.append({"id": change.before.record_id})
            elif (
                change.action == "UPDATE" and change.before is not None and change.after is not None
            ):
                if not change.before.record_id:
                    raise CloudflareDnsError(
                        "cannot update Cloudflare DNS record without record id"
                    )
                puts.append({"id": change.before.record_id, **change.after.api_payload()})
            elif change.action == "CREATE" and change.after is not None:
                posts.append(change.after.api_payload())
            else:
                raise CloudflareDnsError("invalid Cloudflare DNS plan operation")
        self._request(
            "POST",
            f"/zones/{zone_id}/dns_records/batch",
            payload={"deletes": deletes, "puts": puts, "posts": posts, "patches": []},
        )


def _normalize_zone(zone: object) -> str:
    if not isinstance(zone, str) or not zone.strip():
        raise CloudflareDnsError("manifest requires non-empty zone")
    value = zone.strip().lower().rstrip(".")
    labels = value.split(".")
    if len(labels) < 2 or any(not label or len(label) > 63 for label in labels):
        raise CloudflareDnsError("manifest zone is invalid")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if any(
        set(label) - allowed or label.startswith("-") or label.endswith("-") for label in labels
    ):
        raise CloudflareDnsError("manifest zone is invalid")
    return value


def _normalize_name(name: object, zone: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise CloudflareDnsError("DNS record name must be a non-empty string")
    raw = name.strip().lower().rstrip(".")
    if raw == "@":
        return zone
    if raw == zone or raw.endswith("." + zone):
        return raw
    return f"{raw}.{zone}"


def _record_from_manifest(item: object, zone: str) -> DnsRecord:
    if not isinstance(item, dict):
        raise CloudflareDnsError("manifest records must be mappings")
    allowed = {"type", "name", "content", "ttl", "proxied", "priority"}
    unknown = set(item) - allowed
    if unknown:
        raise CloudflareDnsError(
            f"manifest record contains unsupported keys: {', '.join(sorted(unknown))}"
        )
    record_type = item.get("type")
    if not isinstance(record_type, str) or record_type.upper() not in SUPPORTED_TYPES:
        raise CloudflareDnsError("manifest record type is unsupported")
    record_type = record_type.upper()
    name = _normalize_name(item.get("name"), zone)
    content = item.get("content")
    if not isinstance(content, str) or not content:
        raise CloudflareDnsError("manifest record content must be a non-empty string")
    ttl = item.get("ttl", 1)
    if not isinstance(ttl, int) or isinstance(ttl, bool) or (ttl != 1 and not 60 <= ttl <= 86400):
        raise CloudflareDnsError("manifest record ttl must be 1 or between 60 and 86400")
    proxied = item.get("proxied", False)
    if not isinstance(proxied, bool):
        raise CloudflareDnsError("manifest record proxied must be boolean")
    if proxied and record_type not in PROXY_CAPABLE_TYPES:
        raise CloudflareDnsError(f"manifest forbids proxied=true for {record_type}")
    priority = item.get("priority")
    if record_type == "MX":
        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or not 0 <= priority <= 65535
        ):
            raise CloudflareDnsError("manifest MX records require integer priority 0..65535")
    elif priority is not None:
        raise CloudflareDnsError("manifest priority is only supported for MX records")
    return DnsRecord(record_type, name, content, ttl, proxied, priority)


def _validate_manifest_yaml(raw: str) -> None:
    try:
        for token in yaml.scan(raw, Loader=yaml.SafeLoader):
            if isinstance(token, AnchorToken):
                raise CloudflareDnsError("Cloudflare DNS manifest forbids YAML anchors")
            if isinstance(token, AliasToken):
                raise CloudflareDnsError("Cloudflare DNS manifest forbids YAML aliases")
            if isinstance(token, DirectiveToken):
                raise CloudflareDnsError("Cloudflare DNS manifest forbids YAML directives")
        node = yaml.compose(raw, Loader=yaml.SafeLoader)
    except yaml.YAMLError as exc:
        raise CloudflareDnsError("Cloudflare DNS manifest is invalid YAML") from exc
    if node is not None:
        _reject_duplicate_keys(node)


def _reject_duplicate_keys(node: Node) -> None:
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            key = getattr(key_node, "value", None)
            if not isinstance(key, str):
                raise CloudflareDnsError("Cloudflare DNS manifest keys must be scalar strings")
            if key in seen:
                raise CloudflareDnsError(f"Cloudflare DNS manifest contains duplicate key: {key}")
            seen.add(key)
            _reject_duplicate_keys(value_node)
    elif isinstance(node, SequenceNode):
        for item in node.value:
            _reject_duplicate_keys(item)


def load_manifest(path: Path) -> DnsManifest:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CloudflareDnsError(f"cannot read Cloudflare DNS manifest: {path}") from exc
    _validate_manifest_yaml(raw)
    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise CloudflareDnsError("Cloudflare DNS manifest is invalid YAML") from exc
    if not isinstance(document, dict):
        raise CloudflareDnsError("Cloudflare DNS manifest must be a mapping")
    allowed = {"version", "zone", "managed_recordsets", "records"}
    unknown = set(document) - allowed
    if unknown:
        raise CloudflareDnsError(
            f"manifest contains unsupported keys: {', '.join(sorted(unknown))}"
        )
    if document.get("version") != "cybercore.cloudflare-dns/v0.1":
        raise CloudflareDnsError("manifest version must be cybercore.cloudflare-dns/v0.1")
    zone = _normalize_zone(document.get("zone"))

    raw_sets = document.get("managed_recordsets")
    if not isinstance(raw_sets, list) or not raw_sets:
        raise CloudflareDnsError("manifest requires non-empty managed_recordsets")
    managed: list[tuple[str, str]] = []
    for item in raw_sets:
        if not isinstance(item, dict) or set(item) != {"type", "name"}:
            raise CloudflareDnsError("managed_recordsets entries require exactly type and name")
        record_type = item.get("type")
        if not isinstance(record_type, str) or record_type.upper() not in SUPPORTED_TYPES:
            raise CloudflareDnsError("managed recordset type is unsupported")
        managed.append((record_type.upper(), _normalize_name(item.get("name"), zone)))
    if len(set(managed)) != len(managed):
        raise CloudflareDnsError("manifest contains duplicate managed_recordsets")

    raw_records = document.get("records")
    if not isinstance(raw_records, list):
        raise CloudflareDnsError("manifest records must be a list")
    records = tuple(_record_from_manifest(item, zone) for item in raw_records)
    managed_set = set(managed)
    if any(record.recordset() not in managed_set for record in records):
        raise CloudflareDnsError("every desired record must belong to a managed_recordset")
    semantic = [record.semantic_key() for record in records]
    if len(set(semantic)) != len(semantic):
        raise CloudflareDnsError("manifest contains duplicate desired records")

    by_name: dict[str, set[str]] = {}
    for record in records:
        by_name.setdefault(record.name, set()).add(record.record_type)
    for name, types in by_name.items():
        if "CNAME" in types and len(types) > 1:
            raise CloudflareDnsError(
                f"CNAME cannot coexist with other desired record types at {name}"
            )

    return DnsManifest(zone, tuple(managed), records)


def _canonical_plan_payload(zone: str, zone_id: str, changes: tuple[DnsChange, ...]) -> bytes:
    data = {
        "zone": zone,
        "zone_id": zone_id,
        "changes": [change.public_dict() for change in changes],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def build_plan(
    manifest: DnsManifest,
    *,
    zone_id: str,
    current_records: tuple[DnsRecord, ...],
) -> DnsPlan:
    managed = set(manifest.managed_recordsets)
    current = [record for record in current_records if record.recordset() in managed]
    desired = list(manifest.records)
    changes: list[DnsChange] = []

    for recordset in manifest.managed_recordsets:
        current_set = sorted(
            [record for record in current if record.recordset() == recordset],
            key=lambda record: record.semantic_key(),
        )
        desired_set = sorted(
            [record for record in desired if record.recordset() == recordset],
            key=lambda record: record.semantic_key(),
        )
        exact_desired = {record.semantic_key(): record for record in desired_set}
        unmatched_current: list[DnsRecord] = []
        for record in current_set:
            if record.semantic_key() in exact_desired:
                exact_desired.pop(record.semantic_key())
            else:
                unmatched_current.append(record)
        unmatched_desired = sorted(exact_desired.values(), key=lambda record: record.semantic_key())

        pair_count = min(len(unmatched_current), len(unmatched_desired))
        for index in range(pair_count):
            changes.append(
                DnsChange("UPDATE", recordset, unmatched_current[index], unmatched_desired[index])
            )
        for record in unmatched_desired[pair_count:]:
            changes.append(DnsChange("CREATE", recordset, None, record))
        for record in unmatched_current[pair_count:]:
            changes.append(DnsChange("DELETE", recordset, record, None))

    changes_tuple = tuple(changes)
    fingerprint = hashlib.sha256(
        _canonical_plan_payload(manifest.zone, zone_id, changes_tuple)
    ).hexdigest()
    return DnsPlan(manifest.zone, zone_id, changes_tuple, fingerprint)


def discover(api: CloudflareApi, zone: str) -> dict[str, object]:
    normalized = _normalize_zone(zone)
    zone_id, status = api.find_zone(normalized)
    records = api.list_dns_records(zone_id)
    dnssec = api.get_dnssec(zone_id)
    return {
        "zone": normalized,
        "zone_id": zone_id,
        "status": status,
        "dnssec": dnssec,
        "records": [record.public_dict() for record in records],
        "mutation": "none",
    }


def plan_from_manifest(api: CloudflareApi, manifest: DnsManifest) -> DnsPlan:
    zone_id, status = api.find_zone(manifest.zone)
    if status != "active":
        raise CloudflareDnsError("Cloudflare zone is not active")
    return build_plan(manifest, zone_id=zone_id, current_records=api.list_dns_records(zone_id))


def apply_manifest(
    api: CloudflareApi,
    manifest: DnsManifest,
    *,
    expected_plan: str,
    approval: str,
) -> dict[str, object]:
    plan = plan_from_manifest(api, manifest)
    if plan.fingerprint != expected_plan:
        raise CloudflareDnsError(
            "Cloudflare DNS plan drifted; generate a fresh plan and approve its exact fingerprint"
        )
    if approval != plan.approval_text:
        raise CloudflareDnsError(f"remote DNS write requires exact approval: {plan.approval_text}")

    applied = [
        {"action": change.action, "type": change.recordset[0], "name": change.recordset[1]}
        for change in plan.changes
    ]
    if plan.changes:
        api.apply_dns_batch(plan.zone_id, plan.changes)

    verification = plan_from_manifest(api, manifest)
    if verification.changes:
        raise CloudflareDnsError(
            "Cloudflare DNS write completed but post-write verification did not converge"
        )
    return {
        "zone": plan.zone,
        "plan_fingerprint": plan.fingerprint,
        "applied": applied,
        "verified": True,
        "remaining_changes": 0,
    }
