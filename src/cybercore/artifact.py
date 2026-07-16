from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

import zstandard


class ArtifactBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BuildResult:
    artifact_path: Path
    artifact_digest: str
    payload_digest: str
    artifact_id: str


def canonical_json(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _source_files(source: Path) -> list[Path]:
    if not source.is_dir():
        raise ArtifactBuildError(f"source directory not found: {source}")
    result=[]
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ArtifactBuildError(f"symlinks are forbidden: {path.relative_to(source)}")
        if path.is_file():
            rel=PurePosixPath(path.relative_to(source).as_posix())
            if rel.is_absolute() or ".." in rel.parts:
                raise ArtifactBuildError(f"unsafe source path: {rel}")
            result.append(path)
    if not result:
        raise ArtifactBuildError("source directory is empty")
    return result


def _tar_bytes(source: Path) -> bytes:
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in _source_files(source):
            data=path.read_bytes()
            info=tarfile.TarInfo(path.relative_to(source).as_posix())
            info.size=len(data); info.mode=0o755 if path.stat().st_mode & 0o111 else 0o644
            info.uid=0; info.gid=0; info.uname=""; info.gname=""; info.mtime=0; info.pax_headers={}
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _artifact_tar(entries: dict[str, bytes]) -> bytes:
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(entries):
            data=entries[name]
            info=tarfile.TarInfo(name)
            info.size=len(data); info.mode=0o644; info.uid=0; info.gid=0; info.uname=""; info.gname=""; info.mtime=0; info.pax_headers={}
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def build_artifact(source: Path, output_dir: Path, *, artifact_id: str, version: str, publisher_id: str, publisher_name: str, runtime_compatibility: str, risk: str, title: str, description: str, created_at: str|None=None) -> BuildResult:
    source=source.expanduser().resolve(); output_dir=output_dir.expanduser().resolve()
    if not artifact_id.startswith("WB-"):
        raise ArtifactBuildError("artifact_id must start with WB-")
    if risk not in {"low","medium","high","critical"}:
        raise ArtifactBuildError(f"unsupported risk: {risk}")
    payload_tar=_tar_bytes(source)
    payload=zstandard.ZstdCompressor(level=19, write_checksum=True, write_content_size=True, threads=0).compress(payload_tar)
    payload_digest=hashlib.sha256(payload).hexdigest()
    timestamp=created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    manifest={"artifact_id":artifact_id,"compatibility":{"runtime":runtime_compatibility},"created_at":timestamp,"payload":{"compression":"zstd","digest":{"algorithm":"sha256","value":payload_digest},"file":"payload.tar.zst","media_type":"application/vnd.cybercore.payload+tar"},"publisher":{"id":publisher_id,"name":publisher_name},"risk":risk,"schema":"cxp/v1","version":version}
    metadata={"description":description,"rollback_supported":False,"title":title}
    entries={"manifest.json":canonical_json(manifest),"metadata.json":canonical_json(metadata),"payload.tar.zst":payload}
    lines=[f"{hashlib.sha256(entries[name]).hexdigest()}  {name}" for name in sorted(entries)]
    entries["checksums.sha256"]=("\n".join(lines)+"\n").encode()
    artifact=_artifact_tar(entries)
    digest=hashlib.sha256(artifact).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    path=output_dir/f"{artifact_id}.cxp"
    path.write_bytes(artifact)
    return BuildResult(path,digest,payload_digest,artifact_id)
