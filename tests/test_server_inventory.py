from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

from cybercore.execution.server.inventory import (
    MAX_CONTAINERS,
    MAX_DOCKER_COMMAND_OUTPUT_BYTES,
    _read_meminfo,
    _run_bounded_command,
    collect_inventory,
    validate_inventory_payload,
)


def _valid_inventory_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "host": {
            "hostname": "test",
            "cpu_logical": 2,
            "load_1m": 0.1,
            "load_5m": 0.1,
            "load_15m": 0.1,
        },
        "memory": {
            "total_bytes": 1024,
            "available_bytes": 512,
            "swap_total_bytes": 256,
            "swap_free_bytes": 128,
        },
        "root_filesystem": {"total_bytes": 2048, "used_bytes": 1024, "free_bytes": 1024},
        "docker": {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
    }


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


@pytest.mark.parametrize("bad_version", [True, 1.0, "1"])
def test_validator_rejects_non_integer_schema_versions(bad_version: object) -> None:
    payload = {
        "schema_version": bad_version,
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
    }
    with pytest.raises(ValueError):
        validate_inventory_payload(payload)


def test_missing_container_field_is_partial_failure_not_fabricated_data() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            row = {"Names": "vikunja", "Status": "Up", "Ports": "", "Size": "12MB"}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        if argv[1:3] == ["system", "df"]:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"] == []


def test_empty_required_container_field_is_partial_failure() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            row = {
                "Names": "",
                "Image": "vikunja/vikunja:latest",
                "Status": "Up",
                "Ports": "",
                "Size": "12MB",
            }
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps(row) + "\n",
                stderr="",
            )
        if argv[1:3] == ["system", "df"]:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"] == []


def test_whitespace_required_container_field_is_partial_failure() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            row = {
                "Names": "   ",
                "Image": "vikunja/vikunja:latest",
                "Status": "Up",
                "Ports": "",
                "Size": "12MB",
            }
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps(row) + "\n",
                stderr="",
            )
        if argv[1:3] == ["system", "df"]:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["containers"] == []


def test_non_string_storage_field_is_partial_failure_not_stringified() -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["version", "--format"]:
            return subprocess.CompletedProcess(argv, 0, stdout="27.5.1\n", stderr="")
        if argv[1:3] == ["ps", "--size"]:
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        if argv[1:3] == ["system", "df"]:
            row = {
                "Type": "Images",
                "TotalCount": "2",
                "Active": 1,
                "Size": "1GB",
                "Reclaimable": "100MB (10%)",
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row) + "\n", stderr="")
        raise AssertionError(argv)

    payload = collect_inventory(run=fake_run, which=lambda _: "/usr/bin/docker")
    docker = payload["docker"]
    assert isinstance(docker, dict)
    assert docker["access_status"] == "partial_failure"
    assert docker["storage"] == []


def test_meminfo_read_failure_fails_closed(tmp_path) -> None:
    with pytest.raises(ValueError, match="memory inventory is unavailable"):
        _read_meminfo(tmp_path / "missing-meminfo")


def test_meminfo_missing_required_field_fails_closed(tmp_path) -> None:
    path = tmp_path / "meminfo"
    path.write_text(
        "MemTotal: 1024 kB\nMemAvailable: 512 kB\nSwapTotal: 0 kB\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing required fields"):
        _read_meminfo(path)


def test_meminfo_malformed_required_field_fails_closed(tmp_path) -> None:
    path = tmp_path / "meminfo"
    path.write_text(
        "MemTotal: not-a-number kB\nMemAvailable: 512 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="MemTotal is malformed"):
        _read_meminfo(path)


def test_loadavg_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> tuple[float, float, float]:
        raise OSError("load average unavailable")

    monkeypatch.setattr(
        "cybercore.execution.server.inventory.os.getloadavg",
        unavailable,
    )
    with pytest.raises(ValueError, match="load average inventory is unavailable"):
        collect_inventory(which=lambda _: None)


@pytest.mark.parametrize("field", ["load_1m", "load_5m", "load_15m"])
def test_validator_rejects_negative_load_values(field: str) -> None:
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
    }
    host = payload["host"]
    assert isinstance(host, dict)
    host[field] = -0.1
    with pytest.raises(ValueError, match=f"{field} must be non-negative"):
        validate_inventory_payload(payload)


def test_cpu_count_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("cybercore.execution.server.inventory.os.cpu_count", lambda: None)
    with pytest.raises(ValueError, match="logical CPU inventory is unavailable"):
        collect_inventory(which=lambda _: None)


@pytest.mark.parametrize("cpu_logical", [0, -1])
def test_validator_rejects_non_positive_cpu_count(cpu_logical: int) -> None:
    payload = _valid_inventory_payload()
    host = payload["host"]
    assert isinstance(host, dict)
    host["cpu_logical"] = cpu_logical
    with pytest.raises(ValueError, match="cpu_logical"):
        validate_inventory_payload(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("available_bytes", 1025, "available_bytes cannot exceed total_bytes"),
        ("swap_free_bytes", 257, "swap_free_bytes cannot exceed swap_total_bytes"),
    ],
)
def test_validator_rejects_impossible_memory_relationships(
    field: str,
    value: int,
    message: str,
) -> None:
    payload = _valid_inventory_payload()
    memory = payload["memory"]
    assert isinstance(memory, dict)
    memory[field] = value
    with pytest.raises(ValueError, match=message):
        validate_inventory_payload(payload)


@pytest.mark.parametrize(
    "docker",
    [
        {
            "cli_present": False,
            "access_status": "ok",
            "server_version": "27.5.1",
            "containers": [],
            "storage": [],
        },
        {
            "cli_present": True,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
        {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": "27.5.1",
            "containers": [],
            "storage": [],
        },
        {
            "cli_present": True,
            "access_status": "denied_or_unreachable",
            "server_version": "27.5.1",
            "containers": [],
            "storage": [],
        },
        {
            "cli_present": True,
            "access_status": "ok",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
        {
            "cli_present": False,
            "access_status": "partial_failure",
            "server_version": None,
            "containers": [],
            "storage": [],
        },
    ],
)
def test_validator_rejects_inconsistent_docker_states(docker: dict[str, object]) -> None:
    payload = _valid_inventory_payload()
    payload["docker"] = docker
    with pytest.raises(ValueError, match="docker .* state is inconsistent"):
        validate_inventory_payload(payload)


def test_bounded_command_rejects_output_over_hard_limit() -> None:
    with pytest.raises(RuntimeError, match="command output exceeded"):
        _run_bounded_command(
            [
                sys.executable,
                "-c",
                (f"import sys; sys.stdout.write('x' * {MAX_DOCKER_COMMAND_OUTPUT_BYTES + 1024})"),
            ],
            timeout=5,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("used_bytes", 2049, "filesystem used_bytes cannot exceed total_bytes"),
        ("free_bytes", 2049, "filesystem free_bytes cannot exceed total_bytes"),
    ],
)
def test_validator_rejects_filesystem_component_over_total(
    field: str,
    value: int,
    message: str,
) -> None:
    payload = _valid_inventory_payload()
    filesystem = payload["root_filesystem"]
    assert isinstance(filesystem, dict)
    filesystem[field] = value
    with pytest.raises(ValueError, match=message):
        validate_inventory_payload(payload)


def test_validator_rejects_filesystem_sum_over_total() -> None:
    payload = _valid_inventory_payload()
    filesystem = payload["root_filesystem"]
    assert isinstance(filesystem, dict)
    filesystem["used_bytes"] = 1500
    filesystem["free_bytes"] = 1000
    with pytest.raises(ValueError, match=r"used_bytes \+ free_bytes"):
        validate_inventory_payload(payload)


def test_validator_rejects_zero_total_memory() -> None:
    payload = _valid_inventory_payload()
    memory = payload["memory"]
    assert isinstance(memory, dict)
    memory["total_bytes"] = 0
    memory["available_bytes"] = 0
    with pytest.raises(ValueError, match="memory total_bytes must be positive"):
        validate_inventory_payload(payload)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("container", "name"),
        ("container", "image"),
        ("container", "status"),
        ("container", "size"),
        ("storage", "type"),
        ("storage", "total_count"),
        ("storage", "active"),
        ("storage", "size"),
        ("storage", "reclaimable"),
    ],
)
def test_validator_rejects_empty_required_docker_values(section: str, field: str) -> None:
    payload = _valid_inventory_payload()
    payload["docker"] = {
        "cli_present": True,
        "access_status": "ok",
        "server_version": "27.5.1",
        "containers": [
            {
                "name": "vikunja",
                "image": "vikunja/vikunja:latest",
                "status": "Up",
                "ports": "",
                "size": "12MB",
            }
        ],
        "storage": [
            {
                "type": "Images",
                "total_count": "2",
                "active": "1",
                "size": "1GB",
                "reclaimable": "100MB (10%)",
            }
        ],
    }
    docker = payload["docker"]
    assert isinstance(docker, dict)
    rows = docker["containers"] if section == "container" else docker["storage"]
    assert isinstance(rows, list)
    row = rows[0]
    assert isinstance(row, dict)
    row[field] = ""

    with pytest.raises(ValueError, match="must not be empty"):
        validate_inventory_payload(payload)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("container", "name"),
        ("container", "image"),
        ("container", "status"),
        ("container", "size"),
        ("storage", "type"),
        ("storage", "total_count"),
        ("storage", "active"),
        ("storage", "size"),
        ("storage", "reclaimable"),
    ],
)
def test_validator_rejects_whitespace_only_required_docker_values(
    section: str,
    field: str,
) -> None:
    payload = _valid_inventory_payload()
    payload["docker"] = {
        "cli_present": True,
        "access_status": "ok",
        "server_version": "27.5.1",
        "containers": [
            {
                "name": "vikunja",
                "image": "vikunja/vikunja:latest",
                "status": "Up",
                "ports": "",
                "size": "12MB",
            }
        ],
        "storage": [
            {
                "type": "Images",
                "total_count": "2",
                "active": "1",
                "size": "1GB",
                "reclaimable": "100MB (10%)",
            }
        ],
    }
    docker = payload["docker"]
    assert isinstance(docker, dict)
    rows = docker["containers"] if section == "container" else docker["storage"]
    assert isinstance(rows, list)
    row = rows[0]
    assert isinstance(row, dict)
    row[field] = "   "

    with pytest.raises(ValueError, match="must not be empty"):
        validate_inventory_payload(payload)


def test_validator_rejects_whitespace_only_docker_server_version() -> None:
    payload = _valid_inventory_payload()
    payload["docker"] = {
        "cli_present": True,
        "access_status": "ok",
        "server_version": "   ",
        "containers": [],
        "storage": [],
    }

    with pytest.raises(ValueError, match="docker server_version must not be empty"):
        validate_inventory_payload(payload)
