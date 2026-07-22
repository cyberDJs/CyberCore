#!/usr/bin/env bash
set -euo pipefail

SCENARIO="${1:-uc-001}"
OUTPUT_DIR="${CYBERCORE_DEMO_OUTPUT_DIR:-assets/asciinema}"
mkdir -p "$OUTPUT_DIR"

case "$SCENARIO" in
  uc-001)
    COMMAND="python3 demos/uc_001_reality_to_evidence.py"
    OUTPUT="$OUTPUT_DIR/uc-001-reality-to-evidence.cast"
    ;;
  *)
    echo "Unknown scenario: $SCENARIO" >&2
    exit 2
    ;;
esac

if ! command -v asciinema >/dev/null 2>&1; then
  echo "asciinema is required. Install it and retry." >&2
  exit 1
fi

exec asciinema rec "$OUTPUT" \
  --overwrite \
  --cols 110 \
  --rows 32 \
  --command "$COMMAND"
