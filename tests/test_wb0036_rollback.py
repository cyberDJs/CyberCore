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
        self.target = f"/{upload_input.destination[:-1]}"
        self.directories = {"/", self.target}
        self.files: dict[str, dict[str, bytes]] = {
            "/": {},
            self.target: {
                artifact.name: artifact.content for artifact in upload_input.artifacts
            },
        }
        self.mlst_calls: list[str] = []
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
        if path in self.directories:
            entry_type = "dir"
        elif path.startswith(f"{self.target}/"):
            name = path.removeprefix(f"{self.target}/")
            if name not in self.files.get(self.target, {}):
                raise ftplib.error_perm("550 No such file or directory")
            entry_type = "file"
        else:
            raise ftplib.error_perm("550 No such file or directory")
        return f"250-Listing {path}\n type={entry_type}; {path}\n250 End"

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
    def sendcmd(self, cmd: str) -> str:
        response = super().sendcmd(cmd)
        _verb, path = cmd.split(" ", 1)
        if path.endswith("/index.html"):
            return f"250-Listing {path}\n size=1; {path}\n250 End"
        return response


class MetadataFailureFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        _verb, path = cmd.split(" ", 1)
        self.mlst_calls.append(path)
        raise ftplib.error_temp("421 metadata unavailable")


class PermissionDeniedMetadataFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        _verb, path = cmd.split(" ", 1)
        self.mlst_calls.append(path)
        raise ftplib.error_perm("550 Permission denied")


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
    target = fake.target
    before = dict(fake.files[target])

    result, loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert loads == 1
    assert result.upload_input is upload_input
    assert not result.remote_mutation_possible
    assert fake.protected and fake.passive
    assert fake.files[target] == before
    assert fake.mlst_calls == [
        target,
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
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
    target = fake.target
    del fake.files[target]["index.html"]

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.target_present
    assert result.receipt.cleanup_required
    assert result.receipt.present_artifacts == ("cybercore-version.json",)
    assert "cybercore-version.json" in fake.files[target]
    assert fake.mlst_calls == [
        target,
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
    _assert_no_mutation(fake)


def test_missing_target_is_reported_absent_without_enumeration() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = fake.target
    fake.files.pop(target)
    fake.directories.remove(target)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.already_absent
    assert not result.receipt.target_present
    assert not result.receipt.cleanup_required
    assert fake.mlst_calls == [target]
    _assert_no_mutation(fake)


def test_permission_denied_550_is_conservatively_reported_absent() -> None:
    upload_input = _sealed_input()
    fake = PermissionDeniedMetadataFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert result.receipt is not None
    assert result.receipt.already_absent
    assert not result.receipt.target_present
    assert not result.remote_mutation_possible
    _assert_no_mutation(fake)


def test_recovery_probes_only_sealed_canary_and_approved_artifacts() -> None:
    upload_input = _sealed_input()
    fake = FakeRollbackFtps(upload_input)
    target = fake.target
    fake.directories.add("/unrelated-sibling")
    fake.files["/unrelated-sibling"] = {"private.txt": b"unrelated"}
    fake.files[target]["do-not-touch.txt"] = b"unrelated"

    result, _loads = _execute(fake, upload_input=upload_input)

    assert result.rolled_back, result.errors
    assert fake.mlst_calls == [
        target,
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
    assert all("unrelated" not in path for path in fake.mlst_calls)
    assert all("do-not-touch" not in path for path in fake.mlst_calls)
    _assert_no_mutation(fake)


def test_missing_file_type_blocks_without_remote_mutation() -> None:
    upload_input = _sealed_input()
    fake = MissingFileTypeFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "positively proven" in result.errors[0]
    _assert_no_mutation(fake)


def test_metadata_failure_preserves_fail_closed_no_mutation_semantics() -> None:
    upload_input = _sealed_input()
    fake = MetadataFailureFtps(upload_input)

    result, _loads = _execute(fake, upload_input=upload_input)

    assert not result.rolled_back
    assert not result.remote_mutation_possible
    assert "cannot prove rollback target metadata" in result.errors[0]
    assert PASSWORD not in repr(result)
    _assert_no_mutation(fake)
