from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from cybercore.commands.apply import run_apply
from cybercore.commands.verify import run_verify
from cybercore.runtime import RuntimePaths


def create_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-b", "test-branch"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "CyberCore Test"],
        cwd=repo,
        check=True,
    )

    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True)

    return repo


def create_package(root: Path) -> Path:
    package = root / "WB-0100-apply"
    (package / "actions").mkdir(parents=True)

    manifest = {
        "schema": "cxp/v1",
        "id": "WB-0100-apply",
        "title": "Apply Test",
        "risk": "low",
        "target_branch": "test-branch",
    }

    (package / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (package / "README.md").write_text("# Apply\n", encoding="utf-8")
    (package / "actions/verify.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n",
        encoding="utf-8",
    )
    (package / "actions/apply.sh").write_text(
        '#!/usr/bin/env bash\n'
        'printf "applied\\n" > "$CYBERCORE_REPO/applied.txt"\n',
        encoding="utf-8",
    )

    entries = []
    for relative in (
        "manifest.json",
        "README.md",
        "actions/verify.sh",
        "actions/apply.sh",
    ):
        digest = hashlib.sha256(
            (package / relative).read_bytes()
        ).hexdigest()
        entries.append(f"{digest}  {relative}")

    (package / "checksums.sha256").write_text(
        "\n".join(entries) + "\n",
        encoding="utf-8",
    )

    return package


def test_apply_dry_run_does_not_modify_repo(tmp_path: Path) -> None:
    repo = create_repo(tmp_path)
    package = create_package(tmp_path)
    report = run_verify(package)

    paths = RuntimePaths(
        repo=repo,
        exchange_home=tmp_path / "exchange",
        config_file=tmp_path / "exchange.env",
    )

    result = run_apply(report, paths, dry_run=True)

    assert result.dry_run is True
    assert not (repo / "applied.txt").exists()


def test_apply_executes_action(tmp_path: Path) -> None:
    repo = create_repo(tmp_path)
    package = create_package(tmp_path)
    report = run_verify(package)

    paths = RuntimePaths(
        repo=repo,
        exchange_home=tmp_path / "exchange",
        config_file=tmp_path / "exchange.env",
    )

    result = run_apply(report, paths, dry_run=False)

    assert result.returncode == 0
    assert (repo / "applied.txt").read_text(
        encoding="utf-8"
    ) == "applied\n"
