#!/usr/bin/env bash

set -euo pipefail

# 复制自 create-github-release-flow. 版本读 Directory.Build.props, 不要改后面的 tag / dirty 算法.
PACKAGE_NAME="ExampleMod"
TAG_PREFIX="v"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

git_output() {
  local output
  if ! output="$(git "$@" 2>/dev/null)"; then
    return 1
  fi
  output="$(printf '%s' "$output" | tr -d '\r')"
  output="${output#"${output%%[![:space:]]*}"}"
  output="${output%"${output##*[![:space:]]}"}"
  [[ -n "$output" ]] || return 1
  printf '%s\n' "$output"
}

select_version_tag() {
  local tags="$1"
  local line
  if [[ -n "$TAG_PREFIX" ]]; then
    while IFS= read -r line; do
      if [[ "$line" == "$TAG_PREFIX"* ]]; then
        printf '%s\n' "$line"
        return 0
      fi
    done <<< "$tags"
  fi
  while IFS= read -r line; do
    if [[ -n "$line" ]]; then
      printf '%s\n' "$line"
      return 0
    fi
  done <<< "$tags"
  return 1
}

read_package_version() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$root/tools/project_meta.py"
  else
    python "$root/tools/project_meta.py"
  fi
}

describe_latest_tag() {
  if [[ -n "$TAG_PREFIX" ]]; then
    git_output describe --tags --abbrev=0 --match "${TAG_PREFIX}*" HEAD
  else
    git_output describe --tags --abbrev=0 HEAD
  fi
}

strip_tag_prefix() {
  local display="$1"
  if [[ -n "$TAG_PREFIX" && "$display" == "$TAG_PREFIX"* ]]; then
    printf '%s\n' "${display#"$TAG_PREFIX"}"
  else
    printf '%s\n' "$display"
  fi
}

fallback_tag="${TAG_PREFIX}$(read_package_version)"

exact_tag=""
if tags="$(git_output tag --points-at HEAD)"; then
  exact_tag="$(select_version_tag "$tags" || true)"
fi

if [[ -n "$exact_tag" ]]; then
  tag="$exact_tag"
else
  tag="$(describe_latest_tag || true)"
  tag="${tag:-$fallback_tag}"
fi

commit="$(git_output rev-parse --short=7 HEAD || true)"
dirty=false
if [[ -n "$commit" ]]; then
  set +e
  git diff-index --quiet HEAD --
  status=$?
  set -e
  if [[ "$status" -eq 1 ]]; then
    dirty=true
  fi
fi

if [[ -z "$commit" ]]; then
  display="$tag"
elif [[ "$dirty" == true ]]; then
  display="${tag}^${commit}"
elif [[ -n "$exact_tag" ]]; then
  display="$tag"
else
  display="${tag}-${commit}"
fi

strip_tag_prefix "$display"
