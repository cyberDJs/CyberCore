from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from cybercore.execution.server.inventory import (
    MAX_CONTAINERS,
    collect_inventory,
    validate_inventory_payload,
)


def test_collect_inventory_is_bounded_and_structured() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            row = {
                "Names": "vikunja",
                "Image": "vikunja/vikunja:latest",
                "Status": "Up 2 days",
                "Ports": "127.0.0.1:3456->3456/tcp",
                "Size": "12MB",
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        if argv[1:3] == ["system", "df"]:
            row = {
                "Type": "Images",
                "TotalCount": "3",
                "Active": "1",
                "Size": "2GB",
                "Reclaimable": "500MB (25%)",
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    assert payload["schema_version"] == 1
    assert set(payload) == {"schema_version", "host", "memory", "root_filesystem", "docker"}
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] in {"ok", "not_installed"}
    if docker["access_status"] == "ok":
        assert docker["containers"][0]["name"] == "vikunja"


def test_validator_rejects_extra_fields() -> None:
    payload = {
        "schema_version": 1,
        "host": {
            "hostname": "test",
            "cpu_logical": 2,
            "load_1m": 0.1,
            "load_5m": 0.1,
            "load_15m": 0.1,
        },
        "memory": {
            "total_bytes": 1,
            "available_bytes": 1,
            "swap_total_bytes": 0,
            "swap_free_bytes": 0,
        },
        "root_filesystem": {"total_bytes": 1, "used_bytes": 0, "free_bytes": 1},
        "docker": {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
        "unexpected": "nope",
    }
    with pytest.raises(ValueError):
        validate_inventory_payload(payload)


def test_validator_rejects_unbounded_container_list() -> None:
    payload = {
        "schema_version": 1,
        "host": {
            "hostname": "test",
            "cpu_logical": 2,
            "load_1m": 0.1,
            "load_5m": 0.1,
            "load_15m": 0.1,
        },
        "memory": {
            "total_bytes": 1,
            "available_bytes": 1,
            "swap_total_bytes": 0,
            "swap_free_bytes": 0,
        },
        "root_filesystem": {"total_bytes": 1, "used_bytes": 0, "free_bytes": 1},
        "docker": {
            "cli_present": True,
            "access_status": "ok",
            "server_version": "1",
            "containers": [
                {"name": "", "image": "", "status": "", "ports": "", "size": ""}
                for _ in range(MAX_CONTAINERS + 1)
            ],
            "storage": [],
        },
    }
    with pytest.raises(ValueError):
        validate_inventory_payload(payload)


def test_docker_permission_failure_does_not_escalate() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="permission denied")

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] in {"denied_or_unreachable", "not_installed"}
    assert docker["containers"] == []


def test_docker_subcommand_failure_is_reported_as_partial_failure() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="daemon error")
        if argv[1:3] == ["system", "df"]:
            row = {
                "Type": "Images",
                "TotalCount": "2",
                "Active": "1",
                "Size": "1GB",
                "Reclaimable": "100MB (10%)",
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"] == []
    assert docker["storage"][0]["type"] == "Images"


def test_docker_timeout_is_reported_as_partial_failure() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            row = {
                "Names": "vikunja",
                "Image": "vikunja/vikunja:latest",
                "Status": "Up",
                "Ports": "",
                "Size": "12MB",
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        if argv[1:3] == ["system", "df"]:
            raise subprocess.TimeoutExpired(argv, 5)
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"][0]["name"] == "vikunja"
    assert docker["storage"] == []


def test_malformed_docker_row_is_reported_as_partial_failure() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout='{"Names":"vikunja","Image":"vikunja/vikunja:latest","Status":"Up","Ports":"","Size":"12MB"}\n{malformed\n',
                stderr="",
            )
        if argv[1:3] == ["system", "df"]:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"][0]["name"] == "vikunja"


@pytest.mark.parametrize("bad_load", [float("nan"), float("inf"), float("-inf")])
def test_validator_rejects_non_finite_load_values(bad_load: float) -> None:
    payload = {
        "schema_version": 1,
        "host": {
            "hostname": "test",
            "cpu_logical": 2,
            "load_1m": bad_load,
            "load_5m": 0.1,
            "load_15m": 0.1,
        },
        "memory": {
            "total_bytes": 1,
            "available_bytes": 1,
            "swap_total_bytes": 0,
            "swap_free_bytes": 0,
        },
        "root_filesystem": {"total_bytes": 1, "used_bytes": 0, "free_bytes": 1},
        "docker": {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
    }
    with pytest.raises(ValueError, match="must be finite"):
        validate_inventory_payload(payload)


def test_validator_translates_load_overflow_to_value_error() -> None:
    payload = {
        "schema_version": 1,
        "host": {
            "hostname": "test",
            "cpu_logical": 2,
            "load_1m": 10**10000,
            "load_5m": 0.1,
            "load_15m": 0.1,
        },
        "memory": {
            "total_bytes": 1,
            "available_bytes": 1,
            "swap_total_bytes": 0,
            "swap_free_bytes": 0,
        },
        "root_filesystem": {"total_bytes": 1, "used_bytes": 0, "free_bytes": 1},
        "docker": {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
    }
    with pytest.raises(ValueError, match="outside the supported numeric range"):
        validate_inventory_payload(payload)
