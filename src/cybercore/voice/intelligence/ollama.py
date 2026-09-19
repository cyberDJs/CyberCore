from __future__ import annotations

from collections.abc import Callable
import json
from typing import Mapping
from urllib import error, parse, request

from cybercore.voice.intelligence.config import IntelligenceConfig


Transport = Callable[[str, bytes, float], bytes]


class ModelTransportError(RuntimeError):
    pass


def _default_transport(url: str, payload: bytes, timeout_s: float) -> bytes:
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as response:
            return response.read(1_048_577)
    except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
        raise ModelTransportError(f"ollama request failed: {exc}") from exc


def _validate_loopback_base_url(value: str) -> str:
    parsed = parse.urlparse(value)
    if parsed.scheme != "http":
        raise ValueError("ollama base_url must use http for the local-only WB-0039 provider")
    if parsed.username or parsed.password:
        raise ValueError("ollama base_url must not contain credentials")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("ollama base_url must resolve to an explicit loopback hostname")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("ollama base_url must not contain a path, query, or fragment")
    return value.rstrip("/")


class OllamaModelClient:
    def __init__(
        self,
        config: IntelligenceConfig,
        *,
        transport: Transport | None = None,
    ) -> None:
        if not config.enabled:
            raise ValueError("cannot create an Ollama client from disabled intelligence config")
        self.config = config
        self.base_url = _validate_loopback_base_url(config.base_url)
        self.transport = transport or _default_transport

    def complete(
        self,
        *,
        system: str,
        user: str,
        schema: Mapping[str, object] | None = None,
    ) -> str:
        body: dict[str, object] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        if schema is not None:
            body["format"] = dict(schema)
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        raw = self.transport(f"{self.base_url}/api/chat", payload, self.config.timeout_s)
        if len(raw) > 1_048_576:
            raise ModelTransportError("ollama response exceeded the WB-0039 size limit")
        try:
            decoded = json.loads(raw)
            content = decoded["message"]["content"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ModelTransportError("ollama returned an invalid response envelope") from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelTransportError("ollama returned an empty response")
        return content.strip()
