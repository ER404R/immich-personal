#!/usr/bin/env bash
set -euo pipefail

recipe_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$recipe_root/.immich"

if [[ -e "$source_dir" || -L "$source_dir" ]]; then
  printf 'Move the existing checkout before preparing another one: %s\n' "$source_dir" >&2
  exit 1
fi

sha=${1:-}
if [[ -z "$sha" ]]; then
  sha=$(python3 "$recipe_root/scripts/release.py" resolve)
fi

if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf 'Expected a full Immich commit SHA, got %s\n' "$sha" >&2
  exit 1
fi

staging_dir=$(mktemp -d "$source_dir.XXXXXX")
trap 'rm -rf -- "$staging_dir"' EXIT
git -C "$staging_dir" init --quiet
git -C "$staging_dir" remote add origin https://github.com/immich-app/immich.git
git -C "$staging_dir" fetch --depth=1 origin "$sha"
git -C "$staging_dir" -c advice.detachedHead=false checkout --detach "$sha"
bash "$recipe_root/scripts/apply-patches.sh" "$staging_dir"
python3 -c 'import os, sys; os.rename(sys.argv[1], sys.argv[2])' "$staging_dir" "$source_dir"
