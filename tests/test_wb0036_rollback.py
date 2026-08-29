from __future__ import annotations

import ftplib
import hashlib
import json
from typing import cast

from cybercore import first_write_rollback as rollback
from cybercore.first_write_packet import FirstWriteUploadInput, ValidatedFirstWriteArtifact
from cybercore.first_write_runtime import FirstWriteFtpsCredential

RUN_ID = "20260829T120000Z-rb0036"
COMMIT = "b" * 40
HOST = "staging.eimyherrer.com"
USERNAME = "ccwb34@eimyherrer.com"
PASSWORD = "unit-test-only-secret"


def _sealed_input(*, endpoint_hostname: str = HOST) -> FirstWriteUploadInput:
    index = b"<!doctype html><title>CyberCore canary</title>\n"
    marker = (
        json.dumps(
            {
                "repository": "cyberDJs/CyberCore",
                "commit": COMMIT,
                "branch": "main",
                "built_at": "2026-08-29T10:00:00Z",
                "environment": "interserver-shared-hosting-staging",
                "run_id": RUN_ID,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    artifacts = tuple(
        ValidatedFirstWriteArtifact(name, hashlib.sha256(content).hexdigest(), content)
        for name, content in (
            ("cybercore-version.json", marker),
            ("index.html", index),
        )
    )
    return FirstWriteUploadInput(
        source_commit=COMMIT,
        run_id=RUN_ID,
        destination=f"cybercore-canary-{RUN_ID}/",
        protocol="FTPS_EXPLICIT",
        deploy_identity_scope_reference="evidence:wb0034:scope:ftps",
        authorization_reference="approval:wb0034:first-write:test",
        artifacts=artifacts,
        endpoint_hostname=endpoint_hostname,
    )


class FakeSock:
    def version(self) -> str:
        return "TLSv1.3"


class FakeRollbackFtps:
    def __init__(self, upload_input: FirstWriteUploadInput) -> None:
        self.sock = FakeSock()
        self.cwd_path = "/"
        self.directories = {"/", f"/{upload_input.destination[:-1]}"}
        self.files: dict[str, dict[str, bytes]] = {
            "/": {},
            f"/{upload_input.destination[:-1]}": {
                artifact.name: artifact.content for artifact in upload_input.artifacts
            },
        }
        self.delete_calls: list[str] = []
        self.rmd_calls: list[str] = []
        self.connected_host = ""
        self.protected = False
        self.passive = False

    def connect(self, host: str, port: int, timeout: float | None = None):
        self.connected_host = host
        return "ok"

    def auth(self):
        return "ok"

    def login(self, user: str, passwd: str):
        return "ok"

    def prot_p(self):
        self.protected = True
        return "ok"

    def set_pasv(self, val: bool):
        self.passive = val
        return None

    def pwd(self) -> str:
        return self.cwd_path

    def mlsd(self, path: str = "", facts=None):
        listing_path = path or self.cwd_path
        entries: list[tuple[str, dict[str, str]]] = []
        for name in sorted(self.files.get(listing_path, {})):
            entries.append((name, {"type": "file"}))
        prefix = "/" if listing_path == "/" else f"{listing_path}/"
        for candidate in sorted(self.directories):
            if candidate in {"/", listing_path} or not candidate.startswith(prefix):
                continue
            remainder = candidate[len(prefix) :]
            if remainder and "/" not in remainder:
                entries.append((remainder, {"type": "dir"}))
        return iter(entries)

    def delete(self, filename: str):
        self.delete_calls.append(filename)
        directory, _, name = filename.rpartition("/")
        directory = directory or self.cwd_path
        if name not in self.files.get(directory, {}):
            raise ftplib.error_perm("550 missing")
        del self.files[directory][name]
        return "ok"

    def rmd(self, dirname: str):
        self.rmd_calls.append(dirname)
        path = dirname if dirname.startswith("/") else f"/{dirname}"
        if self.files.get(path):
            raise ftplib.error_perm("550 not empty")
        self.files.pop(path, None)
        self.directories.remove(path)
        return "ok"

    def quit(self):
        return "ok"

    def close(self):
        return None


class DeleteReplyLostFtps(FakeRollbackFtps):
    def delete(self, filename: str):
        super().delete(filename)
        raise ftplib.error_temp("421 connection lost after DELE")


class RmdReplyLostFtps(FakeRollbackFtps):
    def rmd(self, dirname: str):
        super().rmd(dirname)
        raise ftplib.error_temp("421 connection lost after RMD")


class MissingFileTypeFtps(FakeRollbackFtps):
    def mlsd(self, path: str = "", facts=None):
        entries = list(super().mlsd(path, facts))
        if path and path != "/":
            return iter((name, {}) for name, _entry_facts in entries)
        return iter(entries)


def _execute(
    fake: FakeRollbackFtps,
    *,
    upload_input: FirstWriteUploadInput,
    authorized: bool = True,
    auth_ref: str | None = None,
    credential: FirstWriteFtpsCredential | None = None,
):
    credential = credential or FirstWriteFtpsCredential(HOST, USERNAME, 21, PASSWORD)
    loads = 0

    def loader():
        nonlocal loads
        loads += 1
        return credential

    result = rollback.execute_first_write_rollback(
        upload_input,
        rollback_authorized=authorized,
        authorization_reference=(
            auth_ref
            if auth_ref is not None
            else rollback.rollback_authorization_reference(upload_input)
        ),
        credential_loader=loader,
        ftp_factory=lambda _context: fake,
    )
    return result, loads


def test_rollback_requires_literal_true_before_loading_secret() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    result, loads = _execute(fake, upload_input=upload_input, authorized=cast(bool, "false"))
    assert not result.rolled_back
    assert loads == 0
    assert fake.connected_host == ""


def test_rollback_requires_exact_run_scoped_authorization_reference() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    result, loads = _execute(fake, upload_input=upload_input, auth_ref="approval:wrong")
    assert not result.rolled_back
    assert loads == 0
    assert "authorization reference" in result.errors[0]


def test_alternate_sealed_endpoint_blocks_before_loading_secret_or_connect() -> None:
    upload_input = _sealed_input(endpoint_hostname="other.example")
    fake = FakeRollbackFtps(upload_input)

    result, loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert loads == 0
    assert fake.connected_host == ""
    assert "approved staging endpoint" in result.errors[0]


def test_rollback_deletes_only_absolute_sealed_artifact_paths_and_exact_directory() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    result, loads = _execute(fake, upload_input=upload_input)

    target = f"/{upload_input.destination[:-1]}"
    assert result.rolled_back, result.errors
    assert loads == 1
    assert result.upload_input is upload_input
    assert fake.protected and fake.passive
    assert fake.delete_calls == [
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
    assert fake.rmd_calls == [target]
    assert target not in fake.directories
    assert result.receipt is not None
    assert result.receipt.deleted_artifacts == ("cybercore-version.json", "index.html")


def test_rollback_allows_missing_artifact_for_interrupted_upload() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    destination = f"/{upload_input.destination[:-1]}"
    del fake.files[destination]["index.html"]

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert fake.delete_calls == [f"{destination}/cybercore-version.json"]
    assert destination not in fake.directories


def test_rollback_is_idempotent_when_exact_directory_is_already_absent() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    destination = f"/{upload_input.destination[:-1]}"
    fake.files.pop(destination)
    fake.directories.remove(destination)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.already_absent
    assert not result.receipt.remote_write_performed
    assert fake.delete_calls == []
    assert fake.rmd_calls == []


def test_unexpected_entry_blocks_before_any_delete() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    destination = f"/{upload_input.destination[:-1]}"
    fake.files[destination]["do-not-delete.txt"] = b"owned by someone else"

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "unexpected entries" in result.errors[0]
    assert fake.delete_calls == []
    assert fake.rmd_calls == []


def test_missing_mlsd_file_type_blocks_before_any_delete() -> None:
    upload_input = _sealed_input()
    fake = MissingFileTypeFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "positively proven" in result.errors[0]
    assert fake.delete_calls == []
    assert fake.rmd_calls == []


def test_delete_reply_loss_preserves_partial_mutation_state() -> None:
    upload_input = _sealed_input()
    fake = DeleteReplyLostFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert result.remote_mutation_possible
    assert result.upload_input is upload_input
    assert result.partial_state is not None
    assert result.partial_state.active_artifact == "cybercore-version.json"
    assert result.partial_state.deleted_artifacts == ()
    assert fake.delete_calls == [
        f"/{upload_input.destination[:-1]}/cybercore-version.json"
    ]
    assert PASSWORD not in repr(result)


def test_rmd_reply_loss_marks_directory_removal_uncertain() -> None:
    upload_input = _sealed_input()
    fake = RmdReplyLostFtps(upload_input)
    destination = f"/{upload_input.destination[:-1]}"

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert result.remote_mutation_possible
    assert result.partial_state is not None
    assert result.partial_state.directory_removal_attempted
    assert result.partial_state.directory_removal_uncertain
    assert result.partial_state.deleted_artifacts == ("cybercore-version.json", "index.html")
    assert fake.rmd_calls == [destination]
    assert destination not in fake.directories
