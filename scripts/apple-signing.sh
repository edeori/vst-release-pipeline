#!/usr/bin/env bash
set -euo pipefail
: "${RUNNER_TEMP:?}" "${CERTIFICATES:?}" "${CERTIFICATES_PASSWORD:?}"
: "${APPLE_ID:?}" "${APPLE_APP_PASSWORD:?}" "${APPLE_TEAM_ID:?}"
keychain="$RUNNER_TEMP/release.keychain-db"
password="$(openssl rand -hex 32)"
echo "::add-mask::$password"
umask 077
printf '%s' "$CERTIFICATES" | base64 --decode > "$RUNNER_TEMP/signing.p12"
security create-keychain -p "$password" "$keychain"
security set-keychain-settings -lut 21600 "$keychain"
security unlock-keychain -p "$password" "$keychain"
security import "$RUNNER_TEMP/signing.p12" -P "$CERTIFICATES_PASSWORD" -A -t cert -f pkcs12 -k "$keychain"
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$password" "$keychain"
security list-keychains -d user -s "$keychain" login.keychain-db
xcrun notarytool store-credentials ci-notary --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" --team-id "$APPLE_TEAM_ID"
rm -f "$RUNNER_TEMP/signing.p12"
