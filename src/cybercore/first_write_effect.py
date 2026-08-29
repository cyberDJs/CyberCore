from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import ssl
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

from cybercore.first_write_packet import FirstWriteUploadInput
from cybercore.first_write_runtime import validate_first_write_upload_input

STAGING_ORIGIN = "https://staging.eimyherrer.com"
MAX_VERIFIER_RESPONSE_BYTES = 1024 * 1024
EXPECTED_VERSION_KEYS = {
    "repository",
    "commit",
    "branch",
    "built_at",
    "environment",
    "run_id",
}

FetchResult = tuple[int, str, bytes]
EffectFetcher = Callable[[str], FetchResult]


@dataclass(frozen=True)
class FirstWriteEffectVerificationResult:
    verified: bool
    errors: tuple[str, ...]
    artifact_sha256: tuple[tuple[str, str], ...] = ()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _default_fetcher(url: str) -> FetchResult:
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    opener = build_opener(HTTPSHandler(context=context), _NoRedirect())
    request = Request(url, headers={"User-Agent": "CyberCore-WB0035-EffectVerifier/1"})
    try:
        with opener.open(request, timeout=15) as response:
            data = response.read(MAX_VERIFIER_RESPONSE_BYTES + 1)
            status = response.status
            final_url = response.geturl()
    except (HTTPError, URLError, OSError, ssl.SSLError):
        raise RuntimeError("HTTPS effect fetch failed") from None
    if len(data) > MAX_VERIFIER_RESPONSE_BYTES:
        raise RuntimeError("HTTPS effect response exceeds size limit")
    return status, final_url, data


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _validate_marker(
    raw_bytes: bytes, upload_input: FirstWriteUploadInput, errors: list[str]
) -> None:
    try:
        loaded = json.loads(raw_bytes.decode("utf-8"), object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        errors.append("served cybercore-version.json is invalid or ambiguous JSON")
        return
    if not isinstance(loaded, dict):
        errors.append("served cybercore-version.json must contain one JSON object")
        return
    marker = cast(dict[str, object], loaded)
    if set(marker) != EXPECTED_VERSION_KEYS:
        errors.append("served cybercore-version.json schema does not match the approved marker")
        return
    expected = {
        "repository": "cyberDJs/CyberCore",
        "commit": upload_input.source_commit,
        "branch": "main",
        "environment": "interserver-shared-hosting-staging",
        "run_id": upload_input.run_id,
    }
    for key, value in expected.items():
        if marker.get(key) != value:
            errors.append(f"served cybercore-version.json {key} does not match sealed packet")

    built_at = marker.get("built_at")
    if not isinstance(built_at, str):
        errors.append("served cybercore-version.json built_at is not a UTC timestamp")
        return
    try:
        timestamp = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    except ValueError:
        errors.append("served cybercore-version.json built_at is not valid ISO-8601")
        return
    if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
        errors.append("served cybercore-version.json built_at must use UTC")


def verify_first_write_effect(
    upload_input: FirstWriteUploadInput,
    *,
    fetcher: EffectFetcher = _default_fetcher,
) -> FirstWriteEffectVerificationResult:
    errors = list(validate_first_write_upload_input(upload_input))
    if errors:
        return FirstWriteEffectVerificationResult(False, tuple(errors))

    expected_artifacts = {artifact.name: artifact for artifact in upload_input.artifacts}
    observed: list[tuple[str, str]] = []
    served: dict[str, bytes] = {}
    for name in ("index.html", "cybercore-version.json"):
        url = f"{STAGING_ORIGIN}/{upload_input.destination}{name}"
        try:
            status, final_url, body = fetcher(url)
        except RuntimeError:
            errors.append(f"HTTPS effect fetch failed: {name}")
            continue
        if status != 200:
            errors.append(f"HTTPS effect status is not 200: {name}")
            continue
        if final_url != url:
            errors.append(f"HTTPS effect verifier rejected redirect or URL drift: {name}")
            continue
        digest = hashlib.sha256(body).hexdigest()
        observed.append((name, digest))
        if digest != expected_artifacts[name].sha256:
            errors.append(f"served artifact hash does not match sealed bytes: {name}")
        served[name] = body

    marker = served.get("cybercore-version.json")
    if marker is not None:
        _validate_marker(marker, upload_input, errors)
    return FirstWriteEffectVerificationResult(not errors, tuple(errors), tuple(observed))
