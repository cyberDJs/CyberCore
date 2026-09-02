from __future__ import annotations

import pytest

from cybercore import first_write_rollback as rollback
from cybercore.first_write_runtime import FirstWriteRuntimeError


class _ResponseOnlyClient:
    def __init__(self, response: str) -> None:
        self.response = response

    def sendcmd(self, _cmd: str) -> str:
        return self.response


def _probe(response: str, path: str) -> None:
    probe = getattr(rollback, "_probe_exact_path")
    probe(_ResponseOnlyClient(response), path, expected_type="dir")


@pytest.mark.parametrize(
    "separator",
    ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"],
)
def test_mlst_rejects_non_lf_line_breaking_characters(separator: str) -> None:
    path = "/cybercore-canary-line-boundary-test"
    response = f"250-Listing {path}{separator} type=dir; {path}\n250 End"

    with pytest.raises(FirstWriteRuntimeError, match="invalid line-breaking characters"):
        _probe(response, path)


def test_mlst_accepts_only_ftplib_lf_boundaries() -> None:
    path = "/cybercore-canary-line-boundary-test"
    response = f"250-Listing {path}\n type=dir; {path}\n250 End"

    _probe(response, path)
