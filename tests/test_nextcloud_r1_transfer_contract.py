from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "deploy" / "cybercore-exec" / "nextcloud-r1-offhost-transfer"
ROLLBACK = ROOT / "deploy" / "cybercore-exec" / "nextcloud-r1-offhost-rollback"
SOURCE = ROOT / "deploy" / "nextcloud-r1-source" / "nextcloud-r1-source-export"
NEXTCLOUD_DEPLOY = ROOT / "deploy" / "cybercore-exec-nextcloud-r1"
NEXTCLOUD_DISPATCHER = (
    ROOT / "src" / "cybercore" / "execution" / "server" / "nextcloud_dispatcher.py"
)


def test_target_transfer_is_fixed_shell_free_and_fail_closed() -> None:
    text = TARGET.read_text()
    assert 'SOURCE_HOST = "162.250.126.107"' in text
    assert 'SOURCE_USER = "eimyherr"' in text
    assert 'TARGET_ROOT = Path("/var/backups/cybercore/nextcloud-r1-113/2026-10-13")' in text
    assert 'SOURCE_ARCHIVE_NAME = "nextcloud.586_28528.2026-10-07_18-30-01.tar.gz"' in text
    assert '"StrictHostKeyChecking=yes"' in text
    assert '"IdentitiesOnly=yes"' in text
    assert "os.O_NOFOLLOW" in text
    assert "os.O_EXCL" in text
    assert "os.replace(PARTIAL_ARCHIVE, TARGET_ARCHIVE)" in text
    assert "select.select(" in text
    assert "STREAM_TIMEOUT_SECONDS = 2400" in text
    assert "shell=False" in text
    assert "shell=True" not in text
    assert "bash -c" not in text
    assert "sh -c" not in text
    assert "/usr/bin/sudo" not in text


def test_source_exporter_is_forced_command_only_and_self_revoking() -> None:
    text = SOURCE.read_text()
    assert (
        'ARCHIVE = Path("/home/eimyherr/softaculous_backups/'
        'nextcloud.586_28528.2026-10-07_18-30-01.tar.gz")' in text
    )
    assert 'KEY_MARKER = "cc-r1-113-temp"' in text
    assert (
        'EXPECTED_FORCED_COMMAND = "/home/eimyherr/.local/libexec/'
        'cybercore-nextcloud-r1-source-export"' in text
    )
    assert 'os.environ.get("SSH_ORIGINAL_COMMAND", "")' in text
    assert 'mode == "metadata"' in text
    assert 'mode == "stream"' in text
    assert 'mode == "revoke"' in text
    assert "_revoke_key()" in text
    assert "_revoke_key(allow_absent=True)" in text
    assert "os.O_NOFOLLOW" in text
    assert "os.replace(temporary, AUTHORIZED_KEYS)" in text
    assert "subprocess" not in text
    assert "shell=True" not in text


def test_rollback_never_deletes_verified_archive() -> None:
    text = ROLLBACK.read_text()
    assert 'PARTIAL_ARCHIVE = TARGET_ROOT / f".{ARCHIVE_NAME}.partial"' in text
    assert "_unlink_regular(PARTIAL_ARCHIVE)" in text
    assert "_unlink_regular(PRIVATE_KEY)" in text
    assert "verified_archive_preserved" in text
    assert "ROLLBACK_BLOCKED_SOURCE_REVOKE" in text
    assert "elif PRIVATE_KEY.exists()" in text
    assert "source_revoked_or_already_absent" in text
    assert "TARGET_ROOT / ARCHIVE_NAME).unlink" not in text
    assert "shell=False" in text
    assert "shell=True" not in text


def test_nextcloud_target_subsystem_is_physically_bound_and_forwarding_disabled() -> None:
    text = (NEXTCLOUD_DEPLOY / "cybercore-exec.subsystem.conf").read_text()
    assert (
        "Subsystem cybercore-exec /usr/bin/python3 "
        "/usr/local/libexec/cybercore-exec/nextcloud_dispatcher.py"
    ) in text
    assert (
        "ForceCommand /usr/bin/python3 /usr/local/libexec/cybercore-exec/nextcloud_dispatcher.py"
    ) in text
    assert "PermitTTY no" in text
    assert "AllowTcpForwarding no" in text
    assert "AllowAgentForwarding no" in text
    assert text.rstrip().endswith("Match all")


def test_nextcloud_dispatcher_never_emits_raw_validation_exception() -> None:
    text = NEXTCLOUD_DISPATCHER.read_text()
    assert '_blocked(str(exc))' not in text
    assert 'except RequestValidationError:' in text
    assert '_blocked("request validation failed")' in text
