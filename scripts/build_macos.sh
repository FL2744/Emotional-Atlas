#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
VERSION="$(cat VERSION)"
"$PYTHON" -m PyInstaller --noconfirm --clean EmotionAtlas.spec
codesign --verify --deep --strict 'dist/Emotional Atlas.app'
"$PYTHON" scripts/check_macos_binaries.py 'dist/Emotional Atlas.app'
mkdir -p release
'dist/Emotional Atlas.app/Contents/MacOS/Emotional Atlas' --smoke-test "$PWD/release/smoke-test.json"
ditto -c -k --sequesterRsrc --keepParent 'dist/Emotional Atlas.app' "release/Emotional-Atlas-v${VERSION}-macOS-arm64.zip"
(cd release && shasum -a 256 "Emotional-Atlas-v${VERSION}-macOS-arm64.zip" > SHA256SUMS.txt)
