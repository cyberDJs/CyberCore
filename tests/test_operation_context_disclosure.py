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
    sanitize_command_arguments,
    sanitize_disclosure_text,
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
        "commit_subject",
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


def test_nested_check_details_are_sanitized_in_standard_mode() -> None:
    payload = _payload()
    payload["checks"] = [
        {
            "name": "repository_identity",
            "passed": False,
            "detail": (
                "Mismatch at /Users/example/private/CyberCore from "
                "https://token:secret@github.com/cyberDJs/CyberCore.git"
            ),
            "credentials": "nested-token",
            "unknown": "/Users/example/private/unknown",
        }
    ]

    disclosed = disclose_context_payload(payload)

    checks = disclosed["checks"]
    assert isinstance(checks, list)
    assert checks[0]["name"] == "repository_identity"
    assert checks[0]["passed"] is False
    assert "/Users/example/private/CyberCore" not in checks[0]["detail"]
    assert "token:secret" not in checks[0]["detail"]
    assert "credentials" not in checks[0]
    assert "unknown" not in checks[0]


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


def test_full_mode_exposes_nested_paths_but_never_url_credentials() -> None:
    payload = _payload()
    payload["checks"] = [
        {
            "name": "repository_identity",
            "passed": False,
            "detail": (
                "Mismatch at /Users/example/private/CyberCore from "
                "https://token:secret@github.com/cyberDJs/CyberCore.git"
            ),
        }
    ]

    disclosed = disclose_context_payload(payload, mode=DisclosureMode.FULL)
    checks = disclosed["checks"]

    assert isinstance(checks, list)
    assert "/Users/example/private/CyberCore" in checks[0]["detail"]
    assert "token:secret" not in checks[0]["detail"]


def test_text_renderer_uses_the_same_disclosure_policy() -> None:
    rendered = render_disclosed_context(_payload())

    assert "trusted: True" in rendered
    assert "repository: [REDACTED]" in rendered
    assert "token-value" not in rendered
    assert "must-not-leak" not in rendered


def test_invalid_disclosure_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        disclose_context_payload(_payload(), mode="invalid")


@pytest.mark.parametrize(
    "value,leaked",
    [
        ("/arbitrary/project/repo", "/arbitrary/project/repo"),
        ("/System/Volumes/Data/Users/jan/repo", "/System/Volumes/Data/Users/jan/repo"),
        ("/Users/jan/repo", "/Users/jan/repo"),
        ("/home/jan/repo", "/home/jan/repo"),
        ("C:\\Users\\jan\\repo", "C:\\Users\\jan\\repo"),
        ("\\\\server\\share\\repo", "\\\\server\\share\\repo"),
        ("file:///Users/jan/repo", "/Users/jan/repo"),
        ("https://token:secret@example.test/org/repo.git", "token:secret"),
        ("http://token:secret@example.test/org/repo.git", "token:secret"),
        ("ssh://user:password@example.test/org/repo.git", "user:password"),
        ("git://token:secret@example.test/org/repo.git", "token:secret"),
        ("token@github.com:org/repo.git", "token@"),
    ],
)
def test_sanitizer_covers_path_and_git_url_forms(value: str, leaked: str) -> None:
    sanitized = sanitize_disclosure_text(value)

    assert leaked not in sanitized


def test_sanitizer_full_mode_keeps_local_paths_but_not_credentials() -> None:
    local_path = "/Users/jan/repo"
    credential_url = "ssh://user:password@example.test/org/repo.git"

    assert sanitize_disclosure_text(local_path, mode=DisclosureMode.FULL) == local_path
    assert "user:password" not in sanitize_disclosure_text(
        credential_url,
        mode=DisclosureMode.FULL,
    )


@pytest.mark.parametrize(
    "value,leaked,preserved",
    [
        (
            "https://example.test/repo?token=abc123",
            "abc123",
            "https://example.test/repo?token=[REDACTED]",
        ),
        (
            "https://example.test/repo?access_token=abc123&ref=main",
            "abc123",
            "ref=main",
        ),
        (
            "ssh://host/repo?password=secret",
            "secret",
            "password=[REDACTED]",
        ),
        (
            "https://example.test/repo#api_key=secret",
            "secret",
            "#api_key=[REDACTED]",
        ),
        (
            "https://example.test/repo?api-key=s%65cret&branch=main",
            "s%65cret",
            "branch=main",
        ),
        (
            "https://example.test/repo?access-key=abc123",
            "abc123",
            "access-key=[REDACTED]",
        ),
        (
            "https://example.test/repo?refresh_token=abc123",
            "abc123",
            "refresh_token=[REDACTED]",
        ),
        (
            "https://example.test/repo?passwd=abc123&credential=secret",
            "abc123",
            "credential=[REDACTED]",
        ),
        (
            "https://example.test/#/callback?access_token=abc123&state=ready",
            "abc123",
            "#/callback?access_token=[REDACTED]&state=ready",
        ),
        (
            "https://example.test/#route?api_key=secret&next=/ok",
            "secret",
            "#route?api_key=[REDACTED]&next=/ok",
        ),
    ],
)
def test_sanitizer_redacts_url_secret_query_and_fragment_values(
    value: str,
    leaked: str,
    preserved: str,
) -> None:
    for mode in DisclosureMode:
        sanitized = sanitize_disclosure_text(value, mode=mode)

        assert leaked not in sanitized
        assert preserved in sanitized


@pytest.mark.parametrize(
    "value,leaked",
    [
        ("/Users/John Doe/Private Repo", "Doe/Private Repo"),
        ('"/System/Volumes/Data/Users/John Doe/repo"', "Doe/repo"),
        ("C:\\Users\\John Doe\\Private Repo", "Doe\\Private Repo"),
        ('"\\\\server\\customer data\\repo"', "customer data\\repo"),
    ],
)
def test_sanitizer_redacts_local_paths_containing_spaces(value: str, leaked: str) -> None:
    for mode in (DisclosureMode.STANDARD, DisclosureMode.REDACTED):
        sanitized = sanitize_disclosure_text(value, mode=mode)

        assert leaked not in sanitized
        assert "[REDACTED_PATH]" in sanitized


@pytest.mark.parametrize(
    "value,leaked,preserved",
    [
        (
            'password="hunter 2" before deploy',
            "hunter 2",
            'password="[REDACTED]" before deploy',
        ),
        (
            "token='abc,def'; keep punctuation",
            "abc,def",
            "token='[REDACTED]'; keep punctuation",
        ),
        (
            "secret=value! keep following prose",
            "value!",
            "secret=[REDACTED] keep following prose",
        ),
        (
            'api_key: "value with spaces" and mode=dev',
            "value with spaces",
            'api_key: "[REDACTED]" and mode=dev',
        ),
        (
            "access-key=abc.def,ghi trailing text",
            "abc.def,ghi",
            "access-key=[REDACTED] trailing text",
        ),
    ],
)
def test_sanitizer_redacts_secret_assignments_without_suffix_leaks(
    value: str,
    leaked: str,
    preserved: str,
) -> None:
    sanitized = sanitize_disclosure_text(value)

    assert leaked not in sanitized
    assert preserved in sanitized


def test_command_argument_sanitizer_redacts_secret_like_values() -> None:
    sanitized = sanitize_command_arguments(
        (
            "pytest",
            "--token",
            "abc123",
            "--password=hunter2",
            "https://user:secret@example.test/repo.git",
            "/Users/jan/repo",
        )
    )

    rendered = " ".join(sanitized)
    assert "abc123" not in rendered
    assert "hunter2" not in rendered
    assert "user:secret" not in rendered
    assert "/Users/jan/repo" not in rendered
