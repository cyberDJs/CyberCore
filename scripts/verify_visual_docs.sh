#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
diagrams_dir="${repo_root}/docs/visual/diagrams"
generated_dir="${repo_root}/docs/visual/generated"
learn_dir="${repo_root}/docs/visual/learn"

expected_diagrams=(
  evidence-lifecycle
  work-block-lifecycle
  security-merge-gate
  architecture-overview
  public-private-overlay
)
media_assets=(
  learn-evidence-lifecycle.webm
  learn-evidence-lifecycle.mp4
  learn-evidence-lifecycle.gif
  learn-evidence-lifecycle-poster.png
)

fail() {
  printf '%s\n' "Visual documentation verification failed: $*" >&2
  exit 1
}

file_size_bytes() {
  case "$(uname -s)" in
    Darwin) stat -f '%z' "$1" ;;
    *) stat -c '%s' "$1" ;;
  esac
}

for script in render_visual_docs.sh capture_learn_demo.sh verify_visual_docs.sh; do
  script_path="${script_dir}/${script}"
  [[ -f "${script_path}" ]] || fail "required script is missing: scripts/${script}"
  head -n 2 "${script_path}" | grep -Fx '#!/usr/bin/env bash' >/dev/null || fail "${script} must use bash"
  head -n 2 "${script_path}" | grep -Fx 'set -euo pipefail' >/dev/null || fail "${script} must enable safe shell behavior"
done

for diagram in "${expected_diagrams[@]}"; do
  [[ -s "${diagrams_dir}/${diagram}.mmd" ]] || fail "missing Mermaid source: ${diagram}.mmd"
done

"${script_dir}/render_visual_docs.sh"

for diagram in "${expected_diagrams[@]}"; do
  svg="${generated_dir}/${diagram}.svg"
  [[ -s "${svg}" ]] || fail "missing or empty generated SVG: ${diagram}.svg"
  if rg -n 'https?://' "${svg}" | rg -v 'http://www\.w3\.org/(2000/svg|1999/xlink)' >/dev/null; then
    fail "generated SVG contains an external network reference: ${diagram}.svg"
  fi
done

for source in "${learn_dir}/index.html" "${learn_dir}/app.js" "${learn_dir}/styles.css"; do
  [[ -s "${source}" ]] || fail "missing Learn source: ${source#"${repo_root}/"}"
  if rg -n 'https?://' "${source}" >/dev/null; then
    fail "Learn source contains a remote resource reference: ${source#"${repo_root}/"}"
  fi
done

if git ls-files | rg -n '(^|/)(node_modules|playwright-browsers|\.tmp|tmp|frames)(/|$)|learn-evidence-lifecycle-browser' >/dev/null; then
  fail "a generated dependency, browser, or capture temporary is tracked"
fi

for readme in "${repo_root}/README.md" "${repo_root}/ARCHITECTURE.md" "${repo_root}/docs/visual/README.md"; do
  [[ -f "${readme}" ]] || fail "required documentation file is missing: ${readme#"${repo_root}/"}"
done

if ! rg -F 'docs/visual/generated/architecture-overview.svg' "${repo_root}/README.md" >/dev/null; then
  fail "README.md does not link to the architecture overview SVG"
fi
if ! rg -F 'docs/visual/' "${repo_root}/ARCHITECTURE.md" >/dev/null; then
  fail "ARCHITECTURE.md does not link to visual documentation"
fi

present_media=0
for asset in "${media_assets[@]}"; do
  [[ -e "${generated_dir}/${asset}" ]] && present_media=$((present_media + 1))
done

if [[ "${present_media}" -eq 0 ]]; then
  printf '%s\n' "Learn media has not been captured yet; media validation is pending."
elif [[ "${present_media}" -ne "${#media_assets[@]}" ]]; then
  fail "Learn media is incomplete; run scripts/capture_learn_demo.sh"
else
  for asset in "${media_assets[@]}"; do
    path="${generated_dir}/${asset}"
    [[ -s "${path}" ]] || fail "generated media is empty: ${asset}"
    printf '%s  %s\n' "$(du -h "${path}" | awk '{print $1}')" "${path#"${repo_root}/"}"
  done

  for entry in \
    "learn-evidence-lifecycle.webm:3145728" \
    "learn-evidence-lifecycle.mp4:3145728" \
    "learn-evidence-lifecycle.gif:5242880"; do
    asset="${entry%%:*}"
    limit="${entry##*:}"
    size="$(file_size_bytes "${generated_dir}/${asset}")"
    if (( size > limit )); then
      printf '%s\n' "Warning: ${asset} exceeds its preferred documentation size limit." >&2
    fi
  done

  if command -v ffprobe >/dev/null 2>&1; then
    for asset in learn-evidence-lifecycle.webm learn-evidence-lifecycle.mp4 learn-evidence-lifecycle.gif learn-evidence-lifecycle-poster.png; do
      path="${generated_dir}/${asset}"
      metadata="$(ffprobe -v error -show_entries stream=width,height:format=duration -of default=noprint_wrappers=1 "${path}")"
      width="$(awk -F= '$1 == "width" { print $2; exit }' <<<"${metadata}")"
      height="$(awk -F= '$1 == "height" { print $2; exit }' <<<"${metadata}")"
      [[ "${width}" == "1280" && "${height}" == "720" ]] || fail "${asset} is not 1280x720"
      if [[ "${asset}" != "learn-evidence-lifecycle-poster.png" ]]; then
        duration="$(awk -F= '$1 == "duration" { print $2; exit }' <<<"${metadata}")"
        awk -v value="${duration}" 'BEGIN { exit !(value >= 8 && value <= 12) }' || fail "${asset} duration is outside 8-12 seconds"
        printf '%s\n' "${asset}: ${width}x${height}, ${duration}s"
      else
        printf '%s\n' "${asset}: ${width}x${height}"
      fi
    done
  else
    printf '%s\n' "ffprobe is unavailable; skipped media dimension and duration validation."
  fi
fi

printf '%s\n' "Visual documentation verification passed."
