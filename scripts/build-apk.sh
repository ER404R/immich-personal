#!/usr/bin/env bash
set -euo pipefail

test -s android/key.jks
: "${FORK_VERSION:?FORK_VERSION must be set}"
: "${FORK_BUILD_NUMBER:?FORK_BUILD_NUMBER must be set}"
: "${ALIAS:?ALIAS must be set}"
: "${ANDROID_KEY_PASSWORD:?ANDROID_KEY_PASSWORD must be set}"
: "${ANDROID_STORE_PASSWORD:?ANDROID_STORE_PASSWORD must be set}"

flutter build apk --release --split-per-abi --target-platform android-arm64 \
  --android-project-arg=force-version-code-ignoring-abi=true \
  --build-name="$FORK_VERSION" --build-number="$FORK_BUILD_NUMBER"
