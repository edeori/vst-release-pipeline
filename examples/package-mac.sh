#!/usr/bin/env bash
# Copy to the source repository's ci/package-mac.sh and adapt these two lines.
set -euo pipefail
bash ./package.sh licensed
installer=build/Release/licensed/PluginName.pkg
mkdir -p dist
cp "$installer" dist/installer.pkg
# The central workflow verifies signature and notarization after this adapter.
