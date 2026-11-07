#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DEVELOPER_ID_APPLICATION:?Set DEVELOPER_ID_APPLICATION to your Developer ID Application certificate name}"
: "${NOTARY_PROFILE:?Set NOTARY_PROFILE to a notarytool Keychain profile}"
export DEVELOPER_ID_APPLICATION
bash scripts/build_macos.sh
'dist/Emotional Atlas.app/Contents/MacOS/Emotional Atlas' --connection-check "$PWD/release/connection-check.json"
"${PYTHON:-python3}" -c 'import json; report=json.load(open("release/connection-check.json")); assert all(item["connected"] for item in report.values()), report'
VERSION="$(cat VERSION)"
APP='dist/Emotional Atlas.app'
ZIP="release/Emotional-Atlas-v${VERSION}-macOS-arm64.zip"
xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait --output-format json > release/notarization.json
"${PYTHON:-python3}" -c 'import json; assert json.load(open("release/notarization.json"))["status"] == "Accepted", "Apple notarization was not accepted"'
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
codesign --verify --deep --strict "$APP"
spctl --assess --type execute --verbose=2 "$APP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
(cd release && shasum -a 256 "Emotional-Atlas-v${VERSION}-macOS-arm64.zip" > SHA256SUMS.txt)
printf '%s\n' "Signed, notarized, stapled release: $ZIP"
