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
        for name, content in (("cybercore-version.json", marker), ("index.html", index))
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
        self.target = f"/{upload_input.destination[:-1]}"
        self.directories = {"/", self.target}
        self.files = {
            self.target: {artifact.name: artifact.content for artifact in upload_input.artifacts}
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
        return "/"

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
        raise AssertionError

    def rmd(self, dirname: str):
        self.rmd_calls.append(dirname)
        raise AssertionError

    def rename(self, fromname: str, toname: str):
        self.rename_calls.append((fromname, toname))
        raise AssertionError

    def quit(self):
        return "ok"

    def close(self):
        return None


class MissingFileTypeFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        response = super().sendcmd(cmd)
        _, path = cmd.split(" ", 1)
        if path.endswith("/index.html"):
            return f"250-Listing {path}\n size=1; {path}\n250 End"
        return response


class MetadataFailureFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        _, path = cmd.split(" ", 1)
        self.mlst_calls.append(path)
        raise ftplib.error_temp("421 metadata unavailable")


class PermissionDeniedMetadataFtps(FakeRollbackFtps):
    def sendcmd(self, cmd: str) -> str:
        _, path = cmd.split(" ", 1)
        self.mlst_calls.append(path)
        raise ftplib.error_perm("550 Permission denied")


def _execute(fake, *, upload_input, authorized=True, auth_ref=None, credential=None):
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
            auth_ref or rollback.rollback_authorization_reference(upload_input)
        ),
        credential_loader=loader,
        ftp_factory=lambda _context: fake,
    )
    return result, loads


def _assert_no_mutation(fake):
    assert fake.delete_calls == []
    assert fake.rmd_calls == []
    assert fake.rename_calls == []


def test_rollback_requires_literal_true_before_loading_secret():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    result, loads = _execute(fake, upload_input=inp, authorized=cast(bool, "false"))
    assert not result.rolled_back and loads == 0 and fake.connected_host == ""


def test_rollback_requires_exact_run_scoped_authorization_reference():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    result, loads = _execute(fake, upload_input=inp, auth_ref="approval:wrong")
    assert not result.rolled_back and loads == 0


def test_alternate_sealed_endpoint_blocks_before_loading_secret_or_connect():
    inp = _sealed_input(endpoint_hostname="other.example")
    fake = FakeRollbackFtps(inp)
    result, loads = _execute(fake, upload_input=inp)
    assert not result.rolled_back and loads == 0 and fake.connected_host == ""


def test_present_canary_establishes_logical_rollback_without_mutation():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    target = fake.target
    result, loads = _execute(fake, upload_input=inp)
    assert result.rolled_back and loads == 1
    assert fake.mlst_calls == [
        target,
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
    assert result.receipt and result.receipt.present_artifacts == (
        "cybercore-version.json",
        "index.html",
    )
    _assert_no_mutation(fake)


def test_missing_artifact_fails_closed_without_mutation():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    target = fake.target
    del fake.files[target]["index.html"]
    result, _ = _execute(fake, upload_input=inp)
    assert not result.rolled_back and result.receipt is None
    assert "cannot prove rollback target metadata" in result.errors[0]
    _assert_no_mutation(fake)


def test_missing_target_550_fails_closed():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    fake.directories.remove(fake.target)
    result, _ = _execute(fake, upload_input=inp)
    assert not result.rolled_back and result.receipt is None
    assert "cannot prove rollback target metadata" in result.errors[0]


def test_permission_denied_550_fails_closed():
    inp = _sealed_input()
    fake = PermissionDeniedMetadataFtps(inp)
    result, _ = _execute(fake, upload_input=inp)
    assert not result.rolled_back and result.receipt is None
    assert "cannot prove rollback target metadata" in result.errors[0]


def test_recovery_probes_only_sealed_canary_and_approved_artifacts():
    inp = _sealed_input()
    fake = FakeRollbackFtps(inp)
    target = fake.target
    fake.directories.add("/unrelated-sibling")
    fake.files[target]["do-not-touch.txt"] = b"unrelated"
    result, _ = _execute(fake, upload_input=inp)
    assert result.rolled_back
    assert fake.mlst_calls == [
        target,
        f"{target}/cybercore-version.json",
        f"{target}/index.html",
    ]
    assert all("do-not-touch" not in path and "unrelated" not in path for path in fake.mlst_calls)
    _assert_no_mutation(fake)


def test_missing_file_type_blocks_without_remote_mutation():
    inp = _sealed_input()
    fake = MissingFileTypeFtps(inp)
    result, _ = _execute(fake, upload_input=inp)
    assert not result.rolled_back and "positively proven" in result.errors[0]
    _assert_no_mutation(fake)


def test_metadata_failure_preserves_fail_closed_no_mutation_semantics():
    inp = _sealed_input()
    fake = MetadataFailureFtps(inp)
    result, _ = _execute(fake, upload_input=inp)
    assert not result.rolled_back and "cannot prove rollback target metadata" in result.errors[0]
    assert PASSWORD not in repr(result)
    _assert_no_mutation(fake)
