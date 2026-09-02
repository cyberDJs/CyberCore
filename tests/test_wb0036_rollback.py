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
        self.mlst_calls: list[str] = []
        self.mlsd_calls: list[str] = []
        self.delete_calls: list[str] = []
        self.rmd_calls: list[str] = []
        self.rename_calls: list[tuple[str, str]] = []
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

    def sendcmd(self, cmd: str) -> str:
        verb, path = cmd.split(" ", 1)
        assert verb == "MLST"
        self.mlst_calls.append(path)
        if path not in self.directories:
            raise ftplib.error_perm("550 No such file or directory")
        return f"250-Listing {path}\n type=dir; {path}\n250 End"

    def mlsd(self, path: str = "", facts=None):
        self.mlsd_calls.append(path)
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
        raise AssertionError("logical rollback must never call DELE")

    def rmd(self, dirname: str):
        self.rmd_calls.append(dirname)
        raise AssertionError("logical rollback must never call RMD")

    def rename(self, fromname: str, toname: str):
        self.rename_calls.append((fromname, toname))
        raise AssertionError("logical rollback must never call RNFR/RNTO")

    def quit(self):
        return "ok"

    def close(self):
        return None


class MissingFileTypeFtps(FakeRollbackFtps):
    def mlsd(self, path: str = "", facts=None):
        entries = list(super().mlsd(path, facts))
        if path and path != "/":
            return iter((name, {}) for name, _entry_facts in entries)
        return iter(entries)


class ListingFailureFtps(FakeRollbackFtps):
    def mlsd(self, path: str = "", facts=None):
        self.mlsd_calls.append(path)
        raise ftplib.error_temp("421 listing unavailable")


class MetadataFailureFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        _verb, path = cmd.split(" ", 1)
        self.mlst_calls.append(path)
        raise ftplib.error_temp("421 metadata unavailable")


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


def _assert_no_mutation(fake: FakeRollbackFtps) -> None:
    assert fake.delete_calls == []
    assert fake.rmd_calls == []
    assert fake.rename_calls == []


def test_rollback_requires_literal_true_before_loading_secret() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    result, loads = _execute(fake, upload_input=upload_input, authorized=cast(bool, "false"))
    assert not result.rolled_back
    assert loads == 0
    assert fake.connected_host == ""
    _assert_no_mutation(fake)


def test_rollback_requires_exact_run_scoped_authorization_reference() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    result, loads = _execute(fake, upload_input=upload_input, auth_ref="approval:wrong")
    assert not result.rolled_back
    assert loads == 0
    assert "authorization reference" in result.errors[0]
    _assert_no_mutation(fake)


def test_alternate_sealed_endpoint_blocks_before_loading_secret_or_connect() -> None:
    upload_input = _sealed_input(endpoint_hostname="other.example")
    fake = FakeRollbackFtps(upload_input)

    result, loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert loads == 0
    assert fake.connected_host == ""
    assert "approved staging endpoint" in result.errors[0]
    _assert_no_mutation(fake)


def test_present_canary_establishes_logical_rollback_without_mutation() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = f"/{upload_input.destination[:-1]}"
    before = dict(fake.files[target])

    result, loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert loads == 1
    assert result.upload_input is upload_input
    assert not result.remote_mutation_possible
    assert fake.protected and fake.passive
    assert fake.files[target] == before
    assert fake.mlst_calls == [target]
    assert fake.mlsd_calls == [target]
    _assert_no_mutation(fake)
    assert result.receipt is not None
    assert result.receipt.target_present
    assert result.receipt.cleanup_required
    assert not result.receipt.already_absent
    assert not result.receipt.remote_write_performed
    assert result.receipt.recovery_mode == "logical-no-promote"
    assert result.receipt.present_artifacts == ("cybercore-version.json", "index.html")


def test_interrupted_upload_is_preserved_for_evidence_without_mutation() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = f"/{upload_input.destination[:-1]}"
    del fake.files[target]["index.html"]

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.target_present
    assert result.receipt.cleanup_required
    assert result.receipt.present_artifacts == ("cybercore-version.json",)
    assert "cybercore-version.json" in fake.files[target]
    assert fake.mlst_calls == [target]
    assert fake.mlsd_calls == [target]
    _assert_no_mutation(fake)


def test_rollback_is_idempotent_when_exact_directory_is_already_absent() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = f"/{upload_input.destination[:-1]}"
    fake.files.pop(target)
    fake.directories.remove(target)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.already_absent
    assert not result.receipt.target_present
    assert not result.receipt.cleanup_required
    assert not result.receipt.remote_write_performed
    assert fake.mlst_calls == [target]
    assert fake.mlsd_calls == []
    _assert_no_mutation(fake)


def test_recovery_never_enumerates_the_staging_parent() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = f"/{upload_input.destination[:-1]}"
    fake.directories.add("/unrelated-sibling")
    fake.files["/unrelated-sibling"] = {"private.txt": b"unrelated"}

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert fake.mlst_calls == [target]
    assert fake.mlsd_calls == [target]
    assert "/" not in fake.mlsd_calls
    assert "" not in fake.mlsd_calls
    _assert_no_mutation(fake)


def test_unexpected_entry_blocks_without_remote_mutation() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = f"/{upload_input.destination[:-1]}"
    fake.files[target]["do-not-touch.txt"] = b"owned by someone else"

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "unexpected entries" in result.errors[0]
    _assert_no_mutation(fake)


def test_missing_mlsd_file_type_blocks_without_remote_mutation() -> None:
    upload_input = _sealed_input()
    fake = MissingFileTypeFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "positively proven" in result.errors[0]
    _assert_no_mutation(fake)


def test_listing_failure_preserves_fail_closed_no_mutation_semantics() -> None:
    upload_input = _sealed_input()
    fake = ListingFailureFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "cannot prove rollback canary state" in result.errors[0]
    assert PASSWORD not in repr(result)
    _assert_no_mutation(fake)


def test_metadata_failure_preserves_fail_closed_no_mutation_semantics() -> None:
    upload_input = _sealed_input()
    fake = MetadataFailureFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "cannot prove rollback target metadata" in result.errors[0]
    assert fake.mlsd_calls == []
    assert PASSWORD not in repr(result)
    _assert_no_mutation(fake)
