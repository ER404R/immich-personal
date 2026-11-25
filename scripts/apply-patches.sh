#!/usr/bin/env bash
set -euo pipefail

recipe_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_dir=${1:?Provide the upstream checkout directory}

for patch in "$recipe_root"/patches/*.patch; do
  printf 'Applying %s\n' "${patch##*/}"
  git -C "$source_dir" apply --index --whitespace=error-all "$patch"
done
