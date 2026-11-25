#!/usr/bin/env bash
set -euo pipefail

apk_path=build/app/outputs/flutter-apk/app-arm64-v8a-release.apk
test -s "$apk_path"
unzip -tq "$apk_path" > /dev/null
native_abis=$(unzip -Z1 "$apk_path" | awk -F/ '$1 == "lib" && $2 != "" { print $2 }' | sort -u)
if [[ "$native_abis" != arm64-v8a ]]; then
  printf 'Expected only arm64-v8a native libraries, found: %s\n' "$native_abis" >&2
  exit 1
fi

sdk_root=${ANDROID_SDK_ROOT:-${ANDROID_HOME:?Android SDK path must be set}}
aapt_path=$(printf '%s\n' "$sdk_root"/build-tools/*/aapt | sort -V | tail -n 1)
test -x "$aapt_path"
badging=$("$aapt_path" dump badging "$apk_path")
grep -q "^package: name='app\.alextran\.immich\.personal' " <<< "$badging"
grep -Fxq "application-label:'Immich'" <<< "$badging"

: "${ALIAS:?ALIAS must be set}"
: "${ANDROID_STORE_PASSWORD:?ANDROID_STORE_PASSWORD must be set}"
certificate=$(mktemp)
trap 'rm -f "$certificate"' EXIT
keytool -exportcert -keystore android/key.jks -alias "$ALIAS" -storepass:env ANDROID_STORE_PASSWORD -file "$certificate"
expected_digest=$(sha256sum "$certificate" | cut -d ' ' -f 1)
signature=$("${aapt_path%/*}/apksigner" verify --print-certs "$apk_path")
apk_digests=$(awk '/Signer.* certificate SHA-256 digest: / && !/^[[:space:]]*Source[[:space:]]*Stamp/ {
  digest = tolower($NF)
  gsub(/:/, "", digest)
  print digest
}' <<< "$signature" | sort -u)
if [[ -z "$apk_digests" ]]; then
  printf 'No APK signer certificate was reported by apksigner.\n' >&2
  exit 1
fi
if [[ "$apk_digests" != "$expected_digest" ]]; then
  printf 'The APK signer does not match the configured release certificate.\n' >&2
  exit 1
fi
du -h "$apk_path"
