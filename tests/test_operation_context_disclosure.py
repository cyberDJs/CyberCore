from __future__ import annotations

import pytest

from cybercore.operation_context_disclosure import (
    DISCLOSURE_FIELDS,
    DisclosureClass,
    DisclosureMode,
    disclose_context_payload,
    disclosure_class,
    disclosure_field,
    render_disclosed_context,
)


def _payload() -> dict[str, object]:
    return {
        "repository": "/Users/example/private/CyberCore",
        "operation": "inspect",
        "risk": "low",
        "branch": "feat/context-disclosure-policy",
        "commit": "abc123",
        "dirty": False,
        "project_kernel_present": True,
        "project_state_present": True,
        "trusted": True,
        "checks": [{"name": "git_repository", "passed": True}],
        "credentials": "token-value",
        "unknown": "must-not-leak",
    }


def test_disclosure_contract_covers_all_context_fields() -> None:
    expected = {
        "repository",
        "operation",
        "risk",
        "branch",
        "commit",
        "dirty",
        "project_kernel_present",
        "project_state_present",
        "trusted",
        "checks",
    }

    assert expected <= {field.name for field in DISCLOSURE_FIELDS}


def test_boolean_contract_fields_are_public() -> None:
    assert disclosure_class("trusted") is DisclosureClass.PUBLIC
    assert disclosure_class("dirty") is DisclosureClass.PUBLIC
    assert disclosure_class("project_kernel_present") is DisclosureClass.PUBLIC
    assert disclosure_class("project_state_present") is DisclosureClass.PUBLIC


def test_repository_path_is_sensitive() -> None:
    assert disclosure_class("repository") is DisclosureClass.SENSITIVE


def test_secret_values_are_never_normal_context_output() -> None:
    assert disclosure_class("credentials") is DisclosureClass.SECRET


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown operation context disclosure field"):
        disclosure_field("unknown")


def test_contract_field_names_are_unique() -> None:
    names = [field.name for field in DISCLOSURE_FIELDS]

    assert len(names) == len(set(names))


def test_standard_mode_preserves_types_and_redacts_sensitive_values() -> None:
    disclosed = disclose_context_payload(_payload())

    assert disclosed["trusted"] is True
    assert disclosed["dirty"] is False
    assert disclosed["checks"] == [{"name": "git_repository", "passed": True}]
    assert disclosed["repository"] == "[REDACTED]"


def test_secret_and_unknown_fields_are_omitted_in_every_mode() -> None:
    for mode in DisclosureMode:
        disclosed = disclose_context_payload(_payload(), mode=mode)

        assert "credentials" not in disclosed
        assert "unknown" not in disclosed


def test_redacted_mode_only_exposes_public_values() -> None:
    disclosed = disclose_context_payload(_payload(), mode=DisclosureMode.REDACTED)

    assert disclosed["trusted"] is True
    assert disclosed["dirty"] is False
    assert disclosed["operation"] == "[REDACTED]"
    assert disclosed["checks"] == "[REDACTED]"
    assert disclosed["repository"] == "[REDACTED]"


def test_full_mode_exposes_sensitive_values_but_not_secrets() -> None:
    disclosed = disclose_context_payload(_payload(), mode=DisclosureMode.FULL)

    assert disclosed["repository"] == "/Users/example/private/CyberCore"
    assert "credentials" not in disclosed


def test_text_renderer_uses_the_same_disclosure_policy() -> None:
    rendered = render_disclosed_context(_payload())

    assert "trusted: True" in rendered
    assert "repository: [REDACTED]" in rendered
    assert "token-value" not in rendered
    assert "must-not-leak" not in rendered


def test_invalid_disclosure_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        disclose_context_payload(_payload(), mode="invalid")
