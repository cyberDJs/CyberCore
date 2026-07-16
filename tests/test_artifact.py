from pathlib import Path
import hashlib, io, json, tarfile
import zstandard
from cybercore.artifact import build_artifact

FIXED="2026-07-16T09:00:00Z"

def source(root: Path) -> Path:
    src=root/"source"; src.mkdir(); (src/"README.md").write_text("# Demo\n")
    script=src/"apply.sh"; script.write_text("#!/usr/bin/env bash\nexit 0\n"); script.chmod(0o755)
    return src

def kwargs():
    return dict(artifact_id="WB-0010-test-artifact",version="1.0.0",publisher_id="cyberdjs",publisher_name="CyberDJS",runtime_compatibility=">=0.1.0a1,<0.2.0",risk="low",title="Test",description="Test",created_at=FIXED)

def test_reproducible(tmp_path: Path):
    src=source(tmp_path); a=build_artifact(src,tmp_path/"a",**kwargs()); b=build_artifact(src,tmp_path/"b",**kwargs())
    assert a.artifact_digest==b.artifact_digest
    assert a.artifact_path.read_bytes()==b.artifact_path.read_bytes()

def test_layout(tmp_path: Path):
    result=build_artifact(source(tmp_path),tmp_path/"out",**kwargs())
    with tarfile.open(result.artifact_path,"r:") as tar:
        assert tar.getnames()==["checksums.sha256","manifest.json","metadata.json","payload.tar.zst"]
        manifest=json.loads(tar.extractfile("manifest.json").read())
        payload=tar.extractfile("payload.tar.zst").read()
    assert manifest["payload"]["digest"]["value"]==hashlib.sha256(payload).hexdigest()
    raw=zstandard.ZstdDecompressor().decompress(payload)
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as tar:
        assert tar.getnames()==["README.md","apply.sh"]
