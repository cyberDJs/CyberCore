from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from cybercore import first_write_packet as packet_module


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "WB0034 Hook Test")
    _git(repo, "config", "user.email", "wb0034-hooks@example.invalid")
    (repo / "source.txt").write_text("initial trusted main\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-m", "initial trusted main")
    return repo


def _init_origin(tmp_path: Path, repo: Path) -> Path:
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    return origin


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _install_reference_transaction_hook(
    hook_dir: Path,
    *,
    poisoned_commit: str,
    remote_ref_file: Path,
    sentinel: Path,
) -> None:
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook = hook_dir / "reference-transaction"
    hook.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "committed" ]; then\n'
        f"  printf '%s\\n' {_shell_quote(poisoned_commit)} > {_shell_quote(str(remote_ref_file))}\n"
        f"  : > {_shell_quote(str(sentinel))}\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    hook.chmod(0o700)


@pytest.mark.parametrize("configured_hooks_path", [False, True])
def test_trusted_main_refresh_disables_reference_transaction_hooks(
    tmp_path: Path,
    configured_hooks_path: bool,
) -> None:
    repo = _init_repo(tmp_path)
    _init_origin(tmp_path, repo)
    initial_commit = _git(repo, "rev-parse", "HEAD")

    (repo / "source.txt").write_text("trusted remote main v2\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-m", "advance trusted remote main")
    trusted_remote_commit = _git(repo, "rev-parse", "HEAD")
    _git(repo, "push", "origin", "main")

    (repo / "source.txt").write_text("untrusted local head\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-m", "untrusted local head")
    untrusted_head = _git(repo, "rev-parse", "HEAD")
    assert untrusted_head != trusted_remote_commit

    _git(repo, "update-ref", "refs/remotes/origin/main", initial_commit)
    remote_ref_file = repo / ".git" / "refs" / "remotes" / "origin" / "main"
    sentinel = tmp_path / "reference-transaction-hook-ran"

    if configured_hooks_path:
        hook_dir = tmp_path / "attacker-hooks"
        _git(repo, "config", "core.hooksPath", str(hook_dir))
    else:
        hook_dir = repo / ".git" / "hooks"

    _install_reference_transaction_hook(
        hook_dir,
        poisoned_commit=untrusted_head,
        remote_ref_file=remote_ref_file,
        sentinel=sentinel,
    )

    assert packet_module._git_refresh_origin_main(repo)
    assert not sentinel.exists()
    assert _git(repo, "rev-parse", "refs/remotes/origin/main") == trusted_remote_commit
    assert _git(repo, "rev-parse", "HEAD") == untrusted_head
