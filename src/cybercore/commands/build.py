from pathlib import Path
from cybercore.artifact import BuildResult, build_artifact

def run_build(source: Path, output: Path, **kwargs) -> BuildResult:
    return build_artifact(source, output, **kwargs)
