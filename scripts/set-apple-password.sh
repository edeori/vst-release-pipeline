#!/usr/bin/env bash
set -euo pipefail
printf 'Apple app-specific password (hidden input): '
IFS= read -rs apple_notary_password
printf '\n'
test -n "$apple_notary_password"
xcrun notarytool history --apple-id "${APPLE_ID:-mothprojectproduction@gmail.com}" --team-id "${APPLE_TEAM_ID:-Y8272MS92K}" --password "$apple_notary_password" >/dev/null
printf '%s' "$apple_notary_password" | gh secret set APPLE_APP_PASSWORD --repo edeori/vst-release-pipeline
unset apple_notary_password
printf 'Notarization credentials validated and stored in the central repository.\n'
