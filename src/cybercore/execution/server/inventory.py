from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Any, Callable, Mapping


INVENTORY_SCHEMA_VERSION = 1
DOCKER_TIMEOUT_SECONDS = 5
MAX_CONTAINERS = 100
MAX_STORAGE_ROWS = 16

RunCallable = Callable[..., subprocess.CompletedProcess[str]]
WhichCallable = Callable[[str], str | None]


def _read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    values: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        key, separator, remainder = line.partition(":")
        if not separator or key not in wanted:
            continue
        parts = remainder.strip().split()
        if not parts:
            continue
        try:
            kib = int(parts[0])
        except ValueError:
            continue
        values[key] = kib * 1024
    return {
        "total_bytes": values.get("MemTotal", 0),
        "available_bytes": values.get("MemAvailable", 0),
        "swap_total_bytes": values.get("SwapTotal", 0),
        "swap_free_bytes": values.get("SwapFree", 0),
    }


def _safe_json_lines(
    value: str,
    *,
    limit: int,
) -> tuple[list[Mapping[str, Any]], bool]:
    rows: list[Mapping[str, Any]] = []
    complete = True
    for line in value.splitlines():
        if len(rows) >= limit:
            break
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            complete = False
            continue
        if not isinstance(parsed, dict):
            complete = False
            continue
        rows.append(parsed)
    return rows, complete


def _docker_inventory(
    run: RunCallable = subprocess.run,
    which: WhichCallable = shutil.which,
) -> dict[str, object]:
    docker = which("docker")
    if docker is None:
        return {
            "cli_present": False,
            "access_status": "not_installed",
            "server_version": None,
            "containers": [],
            "storage": [],
        }

    common = {
        "shell": False,
        "check": False,
        "capture_output": True,
        "text": True,
        "timeout": DOCKER_TIMEOUT_SECONDS,
    }
    try:
        version = run([docker, "version", "--format", "{{.Server.Version}}"], **common)
    except (OSError, subprocess.TimeoutExpired):
        return {
            "cli_present": True,
            "access_status": "denied_or_unreachable",
            "server_version": None,
            "containers": [],
            "storage": [],
        }

    if version.returncode != 0:
        return {
            "cli_present": True,
            "access_status": "denied_or_unreachable",
            "server_version": None,
            "containers": [],
            "storage": [],
        }

    server_version = version.stdout.strip()[:128] or None
    containers: list[dict[str, str]] = []
    storage: list[dict[str, str]] = []
    access_status = "ok"

    try:
        listed = run(
            [docker, "ps", "--size", "--format", "{{json .}}"],
            **common,
        )
        if listed.returncode == 0:
            rows, parsed_ok = _safe_json_lines(listed.stdout, limit=MAX_CONTAINERS)
            for row in rows:
                containers.append(
                    {
                        "name": str(row.get("Names", ""))[:256],
                        "image": str(row.get("Image", ""))[:512],
                        "status": str(row.get("Status", ""))[:256],
                        "ports": str(row.get("Ports", ""))[:1024],
                        "size": str(row.get("Size", ""))[:128],
                    }
                )
            if not parsed_ok:
                access_status = "partial_failure"
        else:
            access_status = "partial_failure"
    except (OSError, subprocess.TimeoutExpired):
        access_status = "partial_failure"
        containers = []

    try:
        usage = run([docker, "system", "df", "--format", "{{json .}}"], **common)
        if usage.returncode == 0:
            rows, parsed_ok = _safe_json_lines(usage.stdout, limit=MAX_STORAGE_ROWS)
            for row in rows:
                storage.append(
                    {
                        "type": str(row.get("Type", ""))[:128],
                        "total_count": str(row.get("TotalCount", ""))[:64],
                        "active": str(row.get("Active", ""))[:64],
                        "size": str(row.get("Size", ""))[:128],
                        "reclaimable": str(row.get("Reclaimable", ""))[:128],
                    }
                )
            if not parsed_ok:
                access_status = "partial_failure"
        else:
            access_status = "partial_failure"
    except (OSError, subprocess.TimeoutExpired):
        access_status = "partial_failure"
        storage = []

    return {
        "cli_present": True,
        "access_status": access_status,
        "server_version": server_version,
        "containers": containers,
        "storage": storage,
    }


def collect_inventory(
    run: RunCallable = subprocess.run,
    which: WhichCallable = shutil.which,
) -> dict[str, object]:
    try:
        load_1m, load_5m, load_15m = os.getloadavg()
    except OSError:
        load_1m = load_5m = load_15m = 0.0

    disk = shutil.disk_usage("/")
    payload: dict[str, object] = {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "host": {
            "hostname": socket.gethostname()[:255],
            "cpu_logical": int(os.cpu_count() or 0),
            "load_1m": float(load_1m),
            "load_5m": float(load_5m),
            "load_15m": float(load_15m),
        },
        "memory": _read_meminfo(),
        "root_filesystem": {
            "total_bytes": int(disk.total),
            "used_bytes": int(disk.used),
            "free_bytes": int(disk.free),
        },
        "docker": _docker_inventory(run, which),
    }
    return validate_inventory_payload(payload)


def _require_exact_dict(
    value: object,
    *,
    keys: set[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} does not match the exact inventory schema")
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _require_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _require_text(value: object, label: str, max_length: int) -> str:
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"{label} must be bounded text")
    return value


def validate_inventory_payload(value: object) -> dict[str, object]:
    root = _require_exact_dict(
        value,
        keys={"schema_version", "host", "memory", "root_filesystem", "docker"},
        label="inventory",
    )
    if root["schema_version"] != INVENTORY_SCHEMA_VERSION:
        raise ValueError("unsupported inventory schema version")

    host = _require_exact_dict(
        root["host"],
        keys={"hostname", "cpu_logical", "load_1m", "load_5m", "load_15m"},
        label="host",
    )
    memory = _require_exact_dict(
        root["memory"],
        keys={"total_bytes", "available_bytes", "swap_total_bytes", "swap_free_bytes"},
        label="memory",
    )
    filesystem = _require_exact_dict(
        root["root_filesystem"],
        keys={"total_bytes", "used_bytes", "free_bytes"},
        label="root_filesystem",
    )
    docker = _require_exact_dict(
        root["docker"],
        keys={"cli_present", "access_status", "server_version", "containers", "storage"},
        label="docker",
    )

    normalized_host = {
        "hostname": _require_text(host["hostname"], "hostname", 255),
        "cpu_logical": _require_int(host["cpu_logical"], "cpu_logical"),
        "load_1m": _require_number(host["load_1m"], "load_1m"),
        "load_5m": _require_number(host["load_5m"], "load_5m"),
        "load_15m": _require_number(host["load_15m"], "load_15m"),
    }
    normalized_memory = {
        key: _require_int(memory[key], key)
        for key in ("total_bytes", "available_bytes", "swap_total_bytes", "swap_free_bytes")
    }
    normalized_filesystem = {
        key: _require_int(filesystem[key], key)
        for key in ("total_bytes", "used_bytes", "free_bytes")
    }

    if not isinstance(docker["cli_present"], bool):
        raise ValueError("docker cli_present must be boolean")
    access_status = _require_text(docker["access_status"], "docker access_status", 64)
    if access_status not in {"ok", "partial_failure", "not_installed", "denied_or_unreachable"}:
        raise ValueError("docker access_status is not allowed")
    version = docker["server_version"]
    if version is not None:
        version = _require_text(version, "docker server_version", 128)

    raw_containers = docker["containers"]
    if not isinstance(raw_containers, list) or len(raw_containers) > MAX_CONTAINERS:
        raise ValueError("docker containers must be a bounded list")
    containers: list[dict[str, str]] = []
    for index, item in enumerate(raw_containers):
        row = _require_exact_dict(
            item,
            keys={"name", "image", "status", "ports", "size"},
            label=f"docker container {index}",
        )
        containers.append(
            {
                "name": _require_text(row["name"], "container name", 256),
                "image": _require_text(row["image"], "container image", 512),
                "status": _require_text(row["status"], "container status", 256),
                "ports": _require_text(row["ports"], "container ports", 1024),
                "size": _require_text(row["size"], "container size", 128),
            }
        )

    raw_storage = docker["storage"]
    if not isinstance(raw_storage, list) or len(raw_storage) > MAX_STORAGE_ROWS:
        raise ValueError("docker storage must be a bounded list")
    storage: list[dict[str, str]] = []
    for index, item in enumerate(raw_storage):
        row = _require_exact_dict(
            item,
            keys={"type", "total_count", "active", "size", "reclaimable"},
            label=f"docker storage {index}",
        )
        storage.append(
            {
                "type": _require_text(row["type"], "storage type", 128),
                "total_count": _require_text(row["total_count"], "storage total_count", 64),
                "active": _require_text(row["active"], "storage active", 64),
                "size": _require_text(row["size"], "storage size", 128),
                "reclaimable": _require_text(row["reclaimable"], "storage reclaimable", 128),
            }
        )

    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "host": normalized_host,
        "memory": normalized_memory,
        "root_filesystem": normalized_filesystem,
        "docker": {
            "cli_present": docker["cli_present"],
            "access_status": access_status,
            "server_version": version,
            "containers": containers,
            "storage": storage,
        },
    }


def main() -> int:
    print(json.dumps(collect_inventory(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
