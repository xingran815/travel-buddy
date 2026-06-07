#!/usr/bin/env bash
# Build a distributable TravelBuddy.dmg that bundles the Python backend.
#
# Usage:  bash scripts/build_dmg.sh
#
# Output: TravelBuddy.dmg at the project root.
#
# Requirements:
#   - Xcode command-line tools (xcodebuild)
#   - The project venv must already be set up (pip install -r requirements.txt)
#   - No Apple Developer ID required — the app is ad-hoc signed and can be
#     opened by right-clicking → Open on other Macs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/.build/dmg_work"
XCODEPROJ="$PROJECT_ROOT/TravelBuddy/TravelBuddy.xcodeproj"
ARCHIVE_PATH="$PROJECT_ROOT/.build/TravelBuddy.xcarchive"
DMG_PATH="$PROJECT_ROOT/TravelBuddy.dmg"

echo "==> Cleaning previous build artefacts"
rm -rf "$BUILD_DIR" "$ARCHIVE_PATH"
mkdir -p "$BUILD_DIR"

echo "==> Building TravelBuddy.app (Release, ad-hoc signed)"
xcodebuild \
  -project "$XCODEPROJ" \
  -scheme TravelBuddy \
  -configuration Release \
  -archivePath "$ARCHIVE_PATH" \
  archive \
  CODE_SIGN_IDENTITY="-" \
  CODE_SIGNING_REQUIRED=NO \
  AD_HOC_CODE_SIGNING_ALLOWED=YES \
  | grep -E "(BUILD|error:|warning: )" || true

APP_SRC="$ARCHIVE_PATH/Products/Applications/TravelBuddy.app"
if [ ! -d "$APP_SRC" ]; then
  echo "ERROR: .app not found at $APP_SRC" >&2
  exit 1
fi

echo "==> Copying .app to staging directory"
cp -R "$APP_SRC" "$BUILD_DIR/TravelBuddy.app"

echo "==> Bundling Python backend into .app/Contents/Resources/backend"
BACKEND_DEST="$BUILD_DIR/TravelBuddy.app/Contents/Resources/backend"
mkdir -p "$BACKEND_DEST"

# Copy the Python package, entry point, and virtual environment
cp -R "$PROJECT_ROOT/app"    "$BACKEND_DEST/app"
cp    "$PROJECT_ROOT/main.py" "$BACKEND_DEST/main.py"
cp -R "$PROJECT_ROOT/venv"   "$BACKEND_DEST/venv"

# Copy .env if present (API keys); skip if not so the .app works without it
if [ -f "$PROJECT_ROOT/.env" ]; then
  cp "$PROJECT_ROOT/.env" "$BACKEND_DEST/.env"
  echo "    Included .env"
else
  echo "    No .env found — skipped (configure via Settings on first launch)"
fi

echo "==> Creating TravelBuddy.dmg"
rm -f "$DMG_PATH"
hdiutil create \
  -volname "TravelBuddy" \
  -srcfolder "$BUILD_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo ""
echo "Done!  →  $DMG_PATH"
echo "Distribute this file. Users mount it, drag TravelBuddy.app to /Applications, and launch."
