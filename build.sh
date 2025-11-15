#!/bin/bash
set -e

echo "🔨 Building WhisperNinja.app with proper macOS permissions..."

# 1️⃣ Reset TCC permissions for the app (non-fatal if bundle isn't registered yet)
tccutil reset All com.whisperninja.app || echo "ℹ️ Skipping TCC reset (bundle may not be registered yet). Continuing..."

# 2️⃣ Clean old builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Clean user config directory (license.json and settings.json)
echo "🧹 Cleaning user config directory..."
rm -rf ~/Library/Application\ Support/WhisperNinja/

# 3️⃣ Create entitlements file for microphone and input monitoring
echo "📝 Creating entitlements file..."
cat > entitlements.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.device.microphone</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.input-monitoring</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
EOF

# 4️⃣ Create info.plist file
echo "📝 Creating info.plist file..."
cat > info.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>WhisperNinja</string>
    <key>CFBundleIdentifier</key>
    <string>com.whisperninja.app</string>
    <key>CFBundleName</key>
    <string>WhisperNinja</string>
    <key>CFBundleDisplayName</key>
    <string>WhisperNinja</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>WhisperNinja needs microphone access to record audio for transcription.</string>
    <key>NSInputMonitoringUsageDescription</key>
    <string>WhisperNinja uses input monitoring to detect hotkeys for recording and transcription.</string>
    <key>NSCameraUsageDescription</key>
    <string>WhisperNinja does not use the camera.</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSAppleEventsUsageDescription</key>
    <string>WhisperNinja needs to control other applications to insert transcribed text.</string>
</dict>
</plist>
EOF

# 4.5️⃣ Update polar.json for production build
echo "📝 Updating polar.json for production..."
python3 << 'PYTHON_EOF'
import json
import os

polar_json_path = "whisperninja/config/polar.json"

if os.path.exists(polar_json_path):
    with open(polar_json_path, 'r') as f:
        config = json.load(f)
    
    # Change POLAR_SERVER to "production" if not already
    if config.get("POLAR_SERVER") != "production":
        config["POLAR_SERVER"] = "production"
        print("  ✓ Changed POLAR_SERVER to 'production'")
    
    # Clear sandbox credentials
    config["POLAR_SANDBOX_ACCESS_TOKEN"] = ""
    config["POLAR_SANDBOX_ORGANIZATION_ID"] = ""
    print("  ✓ Cleared sandbox access token and organization ID")
    
    with open(polar_json_path, 'w') as f:
        json.dump(config, f, indent=4)
    print("  ✓ Updated polar.json")
else:
    print(f"  ⚠️ Warning: {polar_json_path} not found, skipping update")
PYTHON_EOF

# 5️⃣ Build with PyInstaller
echo "🔨 Building with PyInstaller..."
pyinstaller --onedir --windowed --name WhisperNinja --noupx \
  --add-data "whisperninja/assets:whisperninja/assets" \
  --add-data "whisperninja/config:whisperninja/config" \
  --hidden-import pynput \
  --hidden-import pynput.keyboard \
  --hidden-import PyQt6 \
  --hidden-import PyQt6.QtCore \
  --hidden-import PyQt6.QtGui \
  --hidden-import PyQt6.QtWidgets \
  --hidden-import pygame \
  --hidden-import numpy \
  --hidden-import pywhispercpp \
  --hidden-import pywhispercpp.model \
  --hidden-import pyaudio \
  --hidden-import rumps \
  --hidden-import pyperclip \
  --hidden-import cryptography \
  --hidden-import cryptography.hazmat.primitives.ciphers.aead \
  --hidden-import sounddevice \
  --hidden-import AppKit \
  --hidden-import whisperninja.src.audio.audio_recorder \
  --hidden-import whisperninja.src.audio.audio_window \
  --hidden-import whisperninja.src.keyboard.key_manager \
  --hidden-import whisperninja.src.installation.test_permissions \
  --hidden-import whisperninja.src.installation.request_permissions \
  --hidden-import whisperninja.src.ui.menu_bar \
  --hidden-import whisperninja.src.ui.settings_manager \
  --hidden-import whisperninja.src.ui.settings_window \
  --hidden-import whisperninja.src.utils.utils \
  --osx-bundle-identifier com.whisperninja.app \
  whisperninja/main.py

# 6️⃣ Create proper .app bundle structure
echo "📦 Creating .app bundle..."
# Check if PyInstaller created the app bundle or directory
if [ -d "dist/WhisperNinja.app" ]; then
  echo "✅ PyInstaller created .app bundle"
else
  echo "📦 Creating .app bundle from directory..."
  mkdir -p dist/WhisperNinja.app/Contents/MacOS
  mkdir -p dist/WhisperNinja.app/Contents/Resources
  
  # Move the executable
  if [ -f "dist/WhisperNinja/WhisperNinja" ]; then
    mv dist/WhisperNinja/WhisperNinja dist/WhisperNinja.app/Contents/MacOS/
  fi
  
  # Move dependencies (_internal, etc.) to MacOS
  if [ -d "dist/WhisperNinja/_internal" ]; then
    mv dist/WhisperNinja/_internal dist/WhisperNinja.app/Contents/MacOS/
  fi
  
  # Move any other files from whisperninja directory
  if [ -d "dist/WhisperNinja" ]; then
    mv dist/WhisperNinja/* dist/WhisperNinja.app/Contents/MacOS/ 2>/dev/null || true
    rmdir dist/WhisperNinja 2>/dev/null || true
  fi
  
  chmod +x dist/WhisperNinja.app/Contents/MacOS/WhisperNinja
fi

# Copy info.plist
cp info.plist dist/WhisperNinja.app/Contents/Info.plist

# Copy icon
cp whisperninja/assets/icons/icon.icns dist/WhisperNinja.app/Contents/Resources/

# Clean up any leftover whisperninja directory (from PyInstaller onedir)
if [ -d "dist/WhisperNinja" ]; then
  echo "🧹 Removing leftover WhisperNinja directory..."
  rm -rf dist/WhisperNinja
fi

# 7️⃣ Sign the app with entitlements
echo "🔐 Signing app with entitlements..."
codesign --deep --force --sign - --entitlements entitlements.plist dist/WhisperNinja.app

# 8️⃣ Verify the app
echo "✅ Verifying app..."
codesign --verify --verbose dist/WhisperNinja.app

# 9️⃣ Create DMG (using create-dmg if available)
echo "💿 Creating DMG..."
if command -v create-dmg >/dev/null 2>&1; then
  DMG_NAME="WhisperNinja.dmg"
  rm -f "$DMG_NAME"
  create-dmg \
    --volname "WhisperNinja" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --icon "WhisperNinja.app" 175 120 \
    --hide-extension "WhisperNinja.app" \
    --app-drop-link 425 120 \
    "$DMG_NAME" \
    "dist/"
  echo "💿 DMG created: $DMG_NAME"
else
  echo "ℹ️ 'create-dmg' not found. Install with: brew install create-dmg"
  echo "ℹ️ Skipping DMG creation."
fi

# 🔟 Clean up temporary files
echo "🧹 Cleaning up..."
rm -f entitlements.plist info.plist

echo ""
echo "🎉 Build complete!"
echo "📱 App location: dist/WhisperNinja.app"
echo "💿 DMG (if created): ./WhisperNinja.dmg"
echo ""
echo "🔐 Permissions included:"
echo "   • Microphone access"
echo "   • Input monitoring (for hotkeys)"
echo "   • Apple Events (for text insertion)"
echo ""
echo "🚀 To test: open dist/WhisperNinja.app"
echo "   macOS will prompt for permissions on first run"