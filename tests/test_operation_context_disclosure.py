from __future__ import annotations

import pytest

from cybercore.operation_context_disclosure import (
    DISCLOSURE_FIELDS,
    DisclosureClass,
    disclosure_class,
    disclosure_field,
)


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
