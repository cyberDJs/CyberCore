#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
tool_dir="${repo_root}/tools/visual-docs"
output_dir="${repo_root}/docs/visual/generated"

if [[ ! -d "${tool_dir}/node_modules/playwright" ]]; then
  printf '%s\n' "Playwright is missing. Run: (cd ${tool_dir} && npm ci)" >&2
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  printf '%s\n' "FFmpeg is required for Learn capture but was not found on PATH." >&2
  exit 1
fi

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/cybercore-learn-capture.XXXXXX")"
cleanup() { rm -rf -- "${temp_dir}"; }
trap cleanup EXIT

intermediate="${temp_dir}/learn-evidence-lifecycle-browser.webm"
mkdir -p "${output_dir}"
node "${tool_dir}/capture.mjs" "${intermediate}"

ffmpeg -y -i "${intermediate}" -an -c:v libvpx-vp9 -crf 38 -b:v 0 -row-mt 1 -deadline good \
  "${output_dir}/learn-evidence-lifecycle.webm"
ffmpeg -y -i "${intermediate}" -an -c:v libx264 -preset medium -crf 24 -pix_fmt yuv420p -movflags +faststart \
  "${output_dir}/learn-evidence-lifecycle.mp4"
ffmpeg -y -i "${intermediate}" -vf "fps=10,scale=1280:720:flags=lanczos,palettegen=max_colors=64" \
  -frames:v 1 -update 1 "${temp_dir}/palette.png"
ffmpeg -y -i "${intermediate}" -i "${temp_dir}/palette.png" -lavfi "fps=10,scale=1280:720:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4" \
  "${output_dir}/learn-evidence-lifecycle.gif"
ffmpeg -y -ss 00:00:05 -i "${intermediate}" -frames:v 1 -update 1 \
  "${output_dir}/learn-evidence-lifecycle-poster.png"

for asset in \
  "${output_dir}/learn-evidence-lifecycle.webm" \
  "${output_dir}/learn-evidence-lifecycle.mp4" \
  "${output_dir}/learn-evidence-lifecycle.gif" \
  "${output_dir}/learn-evidence-lifecycle-poster.png"; do
  printf '%s  %s\n' "$(du -h "${asset}" | awk '{print $1}')" "${asset#"${repo_root}/"}"
done

warn_if_oversized() {
  local path="$1"
  local limit_bytes="$2"
  local label="$3"
  local size_bytes
  size_bytes="$(stat -f '%z' "${path}")"
  if (( size_bytes > limit_bytes )); then
    printf '%s\n' "Warning: ${label} exceeds its preferred documentation size limit." >&2
  fi
}

warn_if_oversized "${output_dir}/learn-evidence-lifecycle.webm" 3145728 "WebM"
warn_if_oversized "${output_dir}/learn-evidence-lifecycle.mp4" 3145728 "MP4"
warn_if_oversized "${output_dir}/learn-evidence-lifecycle.gif" 5242880 "GIF"

printf '%s\n' "Learn capture completed."
