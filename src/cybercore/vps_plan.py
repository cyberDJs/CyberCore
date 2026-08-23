from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import AliasToken, AnchorToken, DirectiveToken


MAX_YAML_DEPTH = 64
MERGE_TAG = "tag:yaml.org,2002:merge"
YAML_FLOAT_TAG = "tag:yaml.org,2002:float"

PLAN_TOP_LEVEL_KEYS = {
    "version",
    "work_block",
    "provider",
    "mode",
    "public_hostname",
    "platform",
    "slices",
    "os_distro",
    "os_version",
    "control_panel",
    "period_months",
    "quantity",
    "location_id",
    "location_name",
    "budget_ceiling_usd_month",
    "one_time_budget_ceiling_usd",
    "minimum_resources",
    "authority",
    "evidence",
}
PLAN_MINIMUM_RESOURCE_KEYS = {"ram_mib", "disk_gib"}
PLAN_AUTHORITY_KEYS = {
    "provider_contact_allowed",
    "order_allowed",
    "payment_allowed",
    "dns_mutation_allowed",
    "ssh_mutation_allowed",
    "application_deploy_allowed",
    "max_new_vps_count",
}
PLAN_EVIDENCE_KEYS = {"plaintext_secret_values_allowed", "safe_aliases_only"}

QUOTE_TOP_LEVEL_KEYS = {
    "version",
    "work_block",
    "provider",
    "evidence_mode",
    "response_sanitized",
    "secret_values_recorded",
    "provider_contact_performed",
    "order_performed",
    "payment_performed",
    "currency",
    "recurring_price_usd_month",
    "one_time_price_usd",
    "platform",
    "slices",
    "os_distro",
    "os_version",
    "control_panel",
    "period_months",
    "quantity",
    "location_id",
    "location_name",
    "stock_available",
    "resources",
    "public_hostname",
    "quote_reference",
}
QUOTE_RESOURCE_KEYS = {"ram_mib", "disk_gib"}
ALLOWED_QUOTE_EVIDENCE_MODES = {"SYNTHETIC_FIXTURE", "LIVE_READ_ONLY"}

DENIED_LITERAL_PATTERNS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "BEGIN DSA PRIVATE KEY",
    "BEGIN PRIVATE KEY",
    "password:",
    "password=",
    "api_key:",
    "api_key=",
    "x-api-key:",
    "authorization: bearer",
    "private_key:",
    "totp_seed:",
    "recovery_code:",
    "session_cookie:",
)


class _LosslessSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that keeps YAML float lexemes as strings."""


def _construct_lossless_float(loader: yaml.SafeLoader, node: ScalarNode) -> str:
    return loader.construct_scalar(node)


_LosslessSafeLoader.add_constructor(YAML_FLOAT_TAG, _construct_lossless_float)


@dataclass(frozen=True)
class VpsValidationResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def as_text(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = [f"WB-0035 VPS validation: {status}"]
        if self.errors:
            lines.append("errors:")
            lines.extend(f"- {item}" for item in self.errors)
        if self.warnings:
            lines.append("warnings:")
            lines.extend(f"- {item}" for item in self.warnings)
        return "\n".join(lines)


@dataclass(frozen=True)
class PurchaseApprovalPacket:
    work_block: str
    provider: str
    quote_reference: str
    public_hostname: str
    platform: str
    slices: int
    os_distro: str
    os_version: str
    control_panel: str
    period_months: int
    quantity: int
    location_id: int
    location_name: str
    recurring_price_usd_month: str
    one_time_price_usd: str
    purchase_authorized: bool = False
    payment_authorized: bool = False
    requires_explicit_approval: bool = True

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _read_text(path: Path, context: str, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"missing {context}: {path}")
    except UnicodeDecodeError:
        errors.append(f"{context} must be UTF-8: {path}")
    return None


def _reject_denied_literals(text: str, context: str, errors: list[str]) -> None:
    lowered = text.lower()
    for pattern in DENIED_LITERAL_PATTERNS:
        if pattern.lower() in lowered:
            errors.append(f"{context} contains denied secret-like literal pattern: {pattern}")


def _reject_denied_loaded_scalars(
    value: object,
    context: str,
    errors: list[str],
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> None:
    if depth > MAX_YAML_DEPTH:
        errors.append(f"{context} exceeds maximum YAML depth {MAX_YAML_DEPTH}")
        return
    if isinstance(value, str):
        _reject_denied_literals(value, context, errors)
        return
    if not isinstance(value, (dict, list)):
        return
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        errors.append(f"{context} contains recursive YAML data")
        return
    seen.add(identity)
    try:
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str):
                    _reject_denied_literals(key, context, errors)
                _reject_denied_loaded_scalars(item, context, errors, depth=depth + 1, seen=seen)
        else:
            for item in value:
                _reject_denied_loaded_scalars(item, context, errors, depth=depth + 1, seen=seen)
    finally:
        seen.remove(identity)


def _collect_structure_errors(
    node: Node,
    context: str,
    errors: list[str],
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> None:
    if depth > MAX_YAML_DEPTH:
        errors.append(f"{context} exceeds maximum YAML depth {MAX_YAML_DEPTH}")
        return
    if seen is None:
        seen = set()
    identity = id(node)
    if identity in seen:
        errors.append(f"{context} contains recursive YAML node graph")
        return
    seen.add(identity)
    try:
        if isinstance(node, MappingNode):
            keys_seen: set[str] = set()
            for key_node, value_node in node.value:
                if not isinstance(key_node, ScalarNode):
                    errors.append(f"{context} mapping keys must be scalar strings")
                else:
                    key = key_node.value
                    if key == "<<" or key_node.tag == MERGE_TAG:
                        errors.append(f"{context} forbids YAML merge keys")
                    if key in keys_seen:
                        errors.append(f"{context} contains duplicate YAML key: {key}")
                    keys_seen.add(key)
                _collect_structure_errors(
                    value_node,
                    context,
                    errors,
                    depth=depth + 1,
                    seen=seen,
                )
        elif isinstance(node, SequenceNode):
            for item in node.value:
                _collect_structure_errors(
                    item,
                    context,
                    errors,
                    depth=depth + 1,
                    seen=seen,
                )
    finally:
        seen.remove(identity)


def _parse_closed_yaml_text(text: str, context: str) -> tuple[dict[str, object] | None, list[str]]:
    errors: list[str] = []
    _reject_denied_literals(text, context, errors)

    unsafe_yaml_metadata = False
    try:
        for token in yaml.scan(text, Loader=yaml.SafeLoader):
            if isinstance(token, AnchorToken):
                errors.append(f"{context} forbids YAML anchors")
                unsafe_yaml_metadata = True
            elif isinstance(token, AliasToken):
                errors.append(f"{context} forbids YAML aliases")
                unsafe_yaml_metadata = True
            elif isinstance(token, DirectiveToken):
                errors.append(f"{context} forbids YAML directives")
                unsafe_yaml_metadata = True
    except (yaml.YAMLError, RecursionError) as exc:
        errors.append(f"{context} is invalid YAML: {exc}")
        return None, errors

    if unsafe_yaml_metadata:
        return None, errors

    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except (yaml.YAMLError, RecursionError) as exc:
        errors.append(f"{context} is invalid YAML: {exc}")
        return None, errors

    if node is not None:
        try:
            _collect_structure_errors(node, context, errors)
        except RecursionError:
            errors.append(f"{context} exceeds safe YAML recursion limits")
            return None, errors

    if errors:
        return None, errors

    try:
        loaded = yaml.load(text, Loader=_LosslessSafeLoader)
    except (yaml.YAMLError, RecursionError) as exc:
        errors.append(f"{context} is invalid YAML: {exc}")
        return None, errors

    if not isinstance(loaded, dict):
        errors.append(f"{context} must be a YAML mapping")
        return None, errors
    if not all(isinstance(key, str) for key in loaded):
        errors.append(f"{context} keys must be strings")
        return None, errors

    _reject_denied_loaded_scalars(loaded, context, errors)
    return cast(dict[str, object], loaded), errors


def _load_closed_yaml(path: Path, context: str) -> tuple[dict[str, object] | None, list[str]]:
    errors: list[str] = []
    text = _read_text(path, context, errors)
    if text is None:
        return None, errors
    document, parse_errors = _parse_closed_yaml_text(text, context)
    errors.extend(parse_errors)
    return document, errors


def _reject_unknown_keys(
    mapping: dict[str, object], allowed: set[str], context: str, errors: list[str]
) -> None:
    unexpected = sorted(key for key in mapping if key not in allowed)
    if unexpected:
        errors.append(f"{context} contains unexpected keys: {', '.join(unexpected)}")


def _require_exact(
    mapping: dict[str, object], key: str, expected: object, context: str, errors: list[str]
) -> None:
    value = mapping.get(key)
    if type(value) is not type(expected) or value != expected:
        errors.append(f"{context} requires {key}: {expected!r}; got {value!r}")


def _require_mapping(
    mapping: dict[str, object], key: str, context: str, errors: list[str]
) -> dict[str, object] | None:
    value = mapping.get(key)
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        errors.append(f"{context} requires mapping: {key}")
        return None
    return cast(dict[str, object], value)


def _require_positive_int(
    mapping: dict[str, object], key: str, context: str, errors: list[str]
) -> int | None:
    value = mapping.get(key)
    if type(value) is not int or value <= 0:
        errors.append(f"{context} requires positive integer {key}; got {value!r}")
        return None
    return value


def _decimal_value(value: object, label: str, context: str, errors: list[str]) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append(f"{context} requires numeric {label}; got {value!r}")
        return None
    try:
        decimal = Decimal(str(value))
    except InvalidOperation:
        errors.append(f"{context} requires numeric {label}; got {value!r}")
        return None
    if not decimal.is_finite():
        errors.append(f"{context} requires finite numeric {label}; got {value!r}")
        return None
    return decimal


def _require_non_negative_money(
    mapping: dict[str, object], key: str, context: str, errors: list[str]
) -> Decimal | None:
    decimal = _decimal_value(mapping.get(key), key, context, errors)
    if decimal is None:
        return None
    if decimal < 0:
        errors.append(f"{context} requires non-negative {key}; got {decimal}")
        return None

    decimal_tuple = decimal.as_tuple()
    exponent = decimal_tuple.exponent
    if not isinstance(exponent, int):
        errors.append(f"{context} requires valid monetary {key}; got {decimal}")
        return None
    if exponent < -2:
        extra_places = -2 - exponent
        digits = decimal_tuple.digits
        if extra_places >= len(digits):
            has_fractional_cent = any(digit != 0 for digit in digits)
        else:
            has_fractional_cent = any(digit != 0 for digit in digits[-extra_places:])
        if has_fractional_cent:
            errors.append(f"{context} requires whole-cent {key}; got {decimal}")
            return None
    return decimal


def _require_non_empty_string(
    mapping: dict[str, object], key: str, context: str, errors: list[str]
) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context} requires non-empty string {key}; got {value!r}")
        return None
    return value.strip()


def _validate_plan_document(document: dict[str, object], errors: list[str]) -> tuple[str, ...]:
    _reject_unknown_keys(document, PLAN_TOP_LEVEL_KEYS, "VPS plan", errors)
    _require_exact(document, "version", 1, "VPS plan", errors)
    _require_exact(document, "work_block", "WB-0035", "VPS plan", errors)
    _require_exact(document, "provider", "InterServer", "VPS plan", errors)
    _require_exact(document, "mode", "plan_only", "VPS plan", errors)
    _require_exact(document, "public_hostname", "tasks.cyberdjs.org", "VPS plan", errors)
    _require_exact(document, "platform", "kvm", "VPS plan", errors)
    _require_exact(document, "slices", 1, "VPS plan", errors)
    _require_exact(document, "os_distro", "ubuntu", "VPS plan", errors)
    _require_exact(document, "os_version", "ubuntu24", "VPS plan", errors)
    _require_exact(document, "control_panel", "none", "VPS plan", errors)
    _require_exact(document, "period_months", 1, "VPS plan", errors)
    _require_exact(document, "quantity", 1, "VPS plan", errors)
    _require_exact(document, "location_id", 1, "VPS plan", errors)
    _require_exact(document, "location_name", "New Jersey", "VPS plan", errors)

    monthly_budget = _require_non_negative_money(
        document, "budget_ceiling_usd_month", "VPS plan", errors
    )
    if monthly_budget is not None and (monthly_budget <= 0 or monthly_budget > Decimal("3.00")):
        errors.append("VPS plan budget_ceiling_usd_month must be > 0 and <= 3.00")

    one_time_budget = _require_non_negative_money(
        document, "one_time_budget_ceiling_usd", "VPS plan", errors
    )
    if one_time_budget is not None and one_time_budget != Decimal("0.00"):
        errors.append("VPS plan one_time_budget_ceiling_usd must equal 0.00")

    minimum = _require_mapping(document, "minimum_resources", "VPS plan", errors)
    if minimum is not None:
        _reject_unknown_keys(minimum, PLAN_MINIMUM_RESOURCE_KEYS, "minimum_resources", errors)
        ram = _require_positive_int(minimum, "ram_mib", "minimum_resources", errors)
        disk = _require_positive_int(minimum, "disk_gib", "minimum_resources", errors)
        if ram is not None and ram < 2048:
            errors.append("minimum_resources.ram_mib must be at least 2048")
        if disk is not None and disk < 30:
            errors.append("minimum_resources.disk_gib must be at least 30")

    authority = _require_mapping(document, "authority", "VPS plan", errors)
    if authority is not None:
        _reject_unknown_keys(authority, PLAN_AUTHORITY_KEYS, "authority", errors)
        for key in (
            "provider_contact_allowed",
            "order_allowed",
            "payment_allowed",
            "dns_mutation_allowed",
            "ssh_mutation_allowed",
            "application_deploy_allowed",
        ):
            _require_exact(authority, key, False, "authority", errors)
        _require_exact(authority, "max_new_vps_count", 1, "authority", errors)

    evidence = _require_mapping(document, "evidence", "VPS plan", errors)
    if evidence is not None:
        _reject_unknown_keys(evidence, PLAN_EVIDENCE_KEYS, "evidence", errors)
        _require_exact(evidence, "plaintext_secret_values_allowed", False, "evidence", errors)
        _require_exact(evidence, "safe_aliases_only", True, "evidence", errors)

    return (
        "plan is repository-only; it grants no InterServer contact, purchase, payment, DNS, SSH, or deploy authority",
    )


def _validate_quote_document(document: dict[str, object], errors: list[str]) -> tuple[str, ...]:
    _reject_unknown_keys(document, QUOTE_TOP_LEVEL_KEYS, "VPS quote", errors)
    _require_exact(document, "version", 1, "VPS quote", errors)
    _require_exact(document, "work_block", "WB-0035", "VPS quote", errors)
    _require_exact(document, "provider", "InterServer", "VPS quote", errors)

    mode = document.get("evidence_mode")
    if not isinstance(mode, str) or mode not in ALLOWED_QUOTE_EVIDENCE_MODES:
        errors.append(
            "VPS quote evidence_mode must be one of: "
            + ", ".join(sorted(ALLOWED_QUOTE_EVIDENCE_MODES))
        )
    _require_exact(document, "response_sanitized", True, "VPS quote", errors)
    _require_exact(document, "secret_values_recorded", False, "VPS quote", errors)
    _require_exact(document, "order_performed", False, "VPS quote", errors)
    _require_exact(document, "payment_performed", False, "VPS quote", errors)
    if mode == "SYNTHETIC_FIXTURE":
        _require_exact(document, "provider_contact_performed", False, "VPS quote", errors)
    elif mode == "LIVE_READ_ONLY":
        _require_exact(document, "provider_contact_performed", True, "VPS quote", errors)

    _require_exact(document, "currency", "USD", "VPS quote", errors)
    _require_non_negative_money(document, "recurring_price_usd_month", "VPS quote", errors)
    _require_non_negative_money(document, "one_time_price_usd", "VPS quote", errors)
    _require_exact(document, "platform", "kvm", "VPS quote", errors)
    _require_exact(document, "slices", 1, "VPS quote", errors)
    _require_exact(document, "os_distro", "ubuntu", "VPS quote", errors)
    _require_exact(document, "os_version", "ubuntu24", "VPS quote", errors)
    _require_exact(document, "control_panel", "none", "VPS quote", errors)
    _require_exact(document, "period_months", 1, "VPS quote", errors)
    _require_exact(document, "quantity", 1, "VPS quote", errors)
    _require_exact(document, "location_id", 1, "VPS quote", errors)
    _require_exact(document, "location_name", "New Jersey", "VPS quote", errors)
    _require_exact(document, "stock_available", True, "VPS quote", errors)
    _require_exact(document, "public_hostname", "tasks.cyberdjs.org", "VPS quote", errors)
    _require_non_empty_string(document, "quote_reference", "VPS quote", errors)

    resources = _require_mapping(document, "resources", "VPS quote", errors)
    if resources is not None:
        _reject_unknown_keys(resources, QUOTE_RESOURCE_KEYS, "quote resources", errors)
        _require_positive_int(resources, "ram_mib", "quote resources", errors)
        _require_positive_int(resources, "disk_gib", "quote resources", errors)

    if mode == "SYNTHETIC_FIXTURE":
        return ("synthetic quote cannot be used as purchase evidence",)
    return ()


def _validate_loaded_pair(
    plan: dict[str, object],
    quote: dict[str, object],
    errors: list[str],
    warnings: list[str],
) -> None:
    warnings.extend(_validate_plan_document(plan, errors))
    warnings.extend(_validate_quote_document(quote, errors))
    if errors:
        return

    for key in (
        "provider",
        "public_hostname",
        "platform",
        "slices",
        "os_distro",
        "os_version",
        "control_panel",
        "period_months",
        "quantity",
        "location_id",
        "location_name",
    ):
        if quote.get(key) != plan.get(key):
            errors.append(
                f"quote {key} does not match plan: {quote.get(key)!r} != {plan.get(key)!r}"
            )

    monthly = _require_non_negative_money(quote, "recurring_price_usd_month", "VPS quote", errors)
    monthly_budget = _require_non_negative_money(
        plan, "budget_ceiling_usd_month", "VPS plan", errors
    )
    if monthly is not None and monthly_budget is not None and monthly > monthly_budget:
        errors.append(
            f"quote recurring price {monthly} exceeds monthly budget ceiling {monthly_budget}"
        )

    one_time = _require_non_negative_money(quote, "one_time_price_usd", "VPS quote", errors)
    one_time_budget = _require_non_negative_money(
        plan, "one_time_budget_ceiling_usd", "VPS plan", errors
    )
    if one_time is not None and one_time_budget is not None and one_time > one_time_budget:
        errors.append(
            f"quote one-time price {one_time} exceeds one-time budget ceiling {one_time_budget}"
        )

    minimum = plan.get("minimum_resources")
    resources = quote.get("resources")
    if isinstance(minimum, dict) and isinstance(resources, dict):
        for key in ("ram_mib", "disk_gib"):
            required = minimum.get(key)
            actual = resources.get(key)
            if type(required) is int and type(actual) is int and actual < required:
                errors.append(
                    f"quote resources.{key} {actual} is below required minimum {required}"
                )

    if quote.get("evidence_mode") == "SYNTHETIC_FIXTURE":
        warnings.append(
            "comparison uses synthetic evidence; A1 live catalog + quote is still required"
        )


def validate_vps_plan(path: Path) -> VpsValidationResult:
    document, errors = _load_closed_yaml(path, "VPS plan")
    if document is None:
        return VpsValidationResult(False, tuple(errors))
    warnings = _validate_plan_document(document, errors)
    return VpsValidationResult(not errors, tuple(errors), warnings)


def validate_vps_quote(path: Path) -> VpsValidationResult:
    document, errors = _load_closed_yaml(path, "VPS quote")
    if document is None:
        return VpsValidationResult(False, tuple(errors))
    warnings = _validate_quote_document(document, errors)
    return VpsValidationResult(not errors, tuple(errors), warnings)


def validate_plan_and_quote(plan_path: Path, quote_path: Path) -> VpsValidationResult:
    plan, plan_errors = _load_closed_yaml(plan_path, "VPS plan")
    quote, quote_errors = _load_closed_yaml(quote_path, "VPS quote")
    errors = [*plan_errors, *quote_errors]
    warnings: list[str] = []
    if plan is None or quote is None:
        return VpsValidationResult(False, tuple(errors))

    _validate_loaded_pair(plan, quote, errors, warnings)
    return VpsValidationResult(not errors, tuple(errors), tuple(dict.fromkeys(warnings)))


def prepare_purchase_approval_packet(
    plan_path: Path, quote_path: Path
) -> tuple[VpsValidationResult, PurchaseApprovalPacket | None]:
    plan, plan_errors = _load_closed_yaml(plan_path, "VPS plan")
    quote, quote_errors = _load_closed_yaml(quote_path, "VPS quote")
    errors = [*plan_errors, *quote_errors]
    warnings: list[str] = []
    if plan is None or quote is None:
        return VpsValidationResult(False, tuple(errors)), None

    _validate_loaded_pair(plan, quote, errors, warnings)
    if errors:
        return VpsValidationResult(False, tuple(errors), tuple(dict.fromkeys(warnings))), None

    if quote.get("evidence_mode") != "LIVE_READ_ONLY":
        errors.append("purchase approval packet requires LIVE_READ_ONLY quote evidence")
        return VpsValidationResult(False, tuple(errors), tuple(dict.fromkeys(warnings))), None

    quote_reference = _require_non_empty_string(quote, "quote_reference", "VPS quote", errors)
    monthly = _require_non_negative_money(quote, "recurring_price_usd_month", "VPS quote", errors)
    one_time = _require_non_negative_money(quote, "one_time_price_usd", "VPS quote", errors)
    if errors or quote_reference is None or monthly is None or one_time is None:
        return VpsValidationResult(False, tuple(errors), tuple(dict.fromkeys(warnings))), None

    packet = PurchaseApprovalPacket(
        work_block="WB-0035",
        provider="InterServer",
        quote_reference=quote_reference,
        public_hostname=str(plan["public_hostname"]),
        platform=str(plan["platform"]),
        slices=cast(int, plan["slices"]),
        os_distro=str(plan["os_distro"]),
        os_version=str(plan["os_version"]),
        control_panel=str(plan["control_panel"]),
        period_months=cast(int, plan["period_months"]),
        quantity=cast(int, plan["quantity"]),
        location_id=cast(int, plan["location_id"]),
        location_name=str(plan["location_name"]),
        recurring_price_usd_month=f"{monthly:.2f}",
        one_time_price_usd=f"{one_time:.2f}",
    )
    warnings.append("packet is informational only; purchase and payment remain unauthorized")
    return VpsValidationResult(True, (), tuple(dict.fromkeys(warnings))), packet
