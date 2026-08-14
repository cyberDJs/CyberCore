#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
tool_dir="${repo_root}/tools/visual-docs"

if [[ ! -x "${tool_dir}/node_modules/.bin/mmdc" ]]; then
  printf '%s\n' "Visual documentation dependencies are missing. Run: (cd ${tool_dir} && npm ci)" >&2
  exit 1
fi

node "${tool_dir}/render.mjs"
printf '%s\n' "Visual documentation render completed."
