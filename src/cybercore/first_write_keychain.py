from __future__ import annotations

import subprocess
import sys

from cybercore.first_write_runtime import FirstWriteFtpsCredential, FirstWriteRuntimeError

KEYCHAIN_ACCOUNT = "CyberCore-WB0034"
HOST_SERVICE = "INTERSERVER_STAGING_HOST"
USER_SERVICE = "INTERSERVER_STAGING_USER"
PORT_SERVICE = "INTERSERVER_STAGING_PORT"
PASSWORD_SERVICE = "INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD"


def _read_keychain_service(service: str) -> str:
    if sys.platform != "darwin":
        raise FirstWriteRuntimeError("macOS Keychain credential adapter requires macOS")
    try:
        completed = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                KEYCHAIN_ACCOUNT,
                "-s",
                service,
                "-w",
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        raise FirstWriteRuntimeError("cannot read required WB-0034 Keychain alias") from None
    if completed.returncode != 0:
        raise FirstWriteRuntimeError("required WB-0034 Keychain alias is unavailable")
    raw = completed.stdout
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if raw.endswith(b"\r"):
        raw = raw[:-1]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise FirstWriteRuntimeError("WB-0034 Keychain alias is not valid UTF-8") from None
    if not value:
        raise FirstWriteRuntimeError("WB-0034 Keychain alias is empty")
    return value


def load_interserver_staging_ftps_credential() -> FirstWriteFtpsCredential:
    host = _read_keychain_service(HOST_SERVICE)
    username = _read_keychain_service(USER_SERVICE)
    port_text = _read_keychain_service(PORT_SERVICE)
    password = _read_keychain_service(PASSWORD_SERVICE)
    try:
        port = int(port_text)
    except ValueError:
        raise FirstWriteRuntimeError("WB-0034 staging port alias is invalid") from None
    return FirstWriteFtpsCredential(
        endpoint_hostname=host,
        username=username,
        port=port,
        password=password,
    )
