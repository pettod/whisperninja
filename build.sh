#!/bin/bash
set -e

echo "🔨 Building whisperninja.app with proper macOS permissions..."

# 1️⃣ Reset TCC permissions for the app (non-fatal if bundle isn't registered yet)
tccutil reset All com.whisperninja.app || echo "ℹ️ Skipping TCC reset (bundle may not be registered yet). Continuing..."

# 2️⃣ Clean old builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

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
    <string>whisperninja</string>
    <key>CFBundleIdentifier</key>
    <string>com.whisperninja.app</string>
    <key>CFBundleName</key>
    <string>whisperninja</string>
    <key>CFBundleDisplayName</key>
    <string>whisperninja</string>
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
    <string>whisperninja needs microphone access to record audio for transcription.</string>
    <key>NSInputMonitoringUsageDescription</key>
    <string>whisperninja uses input monitoring to detect hotkeys for recording and transcription.</string>
    <key>NSCameraUsageDescription</key>
    <string>whisperninja does not use the camera.</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSAppleEventsUsageDescription</key>
    <string>whisperninja needs to control other applications to insert transcribed text.</string>
</dict>
</plist>
EOF

# 5️⃣ Build with PyInstaller
echo "🔨 Building with PyInstaller..."
pyinstaller --onedir --windowed --name whisperninja --noupx \
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
  --hidden-import whisperninja.audio_recorder \
  --hidden-import whisperninja.audio_window \
  --hidden-import whisperninja.key_manager \
  --hidden-import whisperninja.menu_bar \
  --hidden-import whisperninja.settings_manager \
  --hidden-import whisperninja.settings_window \
  --hidden-import whisperninja.utils \
  --osx-bundle-identifier com.whisperninja.app \
  whisperninja/main.py

# 6️⃣ Create proper .app bundle structure
echo "📦 Creating .app bundle..."
# Check if PyInstaller created the app bundle or directory
if [ -d "dist/whisperninja.app" ]; then
  echo "✅ PyInstaller created .app bundle"
else
  echo "📦 Creating .app bundle from directory..."
  mkdir -p dist/whisperninja.app/Contents/MacOS
  mkdir -p dist/whisperninja.app/Contents/Resources
  
  # Move the executable
  if [ -f "dist/whisperninja/whisperninja" ]; then
    mv dist/whisperninja/whisperninja dist/whisperninja.app/Contents/MacOS/
  fi
  
  # Move dependencies (_internal, etc.) to MacOS
  if [ -d "dist/whisperninja/_internal" ]; then
    mv dist/whisperninja/_internal dist/whisperninja.app/Contents/MacOS/
  fi
  
  # Move any other files from whisperninja directory
  if [ -d "dist/whisperninja" ]; then
    mv dist/whisperninja/* dist/whisperninja.app/Contents/MacOS/ 2>/dev/null || true
    rmdir dist/whisperninja 2>/dev/null || true
  fi
  
  chmod +x dist/whisperninja.app/Contents/MacOS/whisperninja
fi

# Copy info.plist
cp info.plist dist/whisperninja.app/Contents/Info.plist

# Copy icon
cp whisperninja/assets/icons/icon.icns dist/whisperninja.app/Contents/Resources/

# Clean up any leftover whisperninja directory (from PyInstaller onedir)
if [ -d "dist/whisperninja" ]; then
  echo "🧹 Removing leftover whisperninja directory..."
  rm -rf dist/whisperninja
fi

# 7️⃣ Sign the app with entitlements
echo "🔐 Signing app with entitlements..."
codesign --deep --force --sign - --entitlements entitlements.plist dist/whisperninja.app

# 8️⃣ Verify the app
echo "✅ Verifying app..."
codesign --verify --verbose dist/whisperninja.app

# 9️⃣ Create DMG (using create-dmg if available)
echo "💿 Creating DMG..."
if command -v create-dmg >/dev/null 2>&1; then
  DMG_NAME="whisperninja.dmg"
  rm -f "$DMG_NAME"
  create-dmg \
    --volname "whisperninja" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --icon "whisperninja.app" 175 120 \
    --hide-extension "whisperninja.app" \
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
echo "📱 App location: dist/whisperninja.app"
echo "💿 DMG (if created): ./whisperninja.dmg"
echo ""
echo "🔐 Permissions included:"
echo "   • Microphone access"
echo "   • Input monitoring (for hotkeys)"
echo "   • Apple Events (for text insertion)"
echo ""
echo "🚀 To test: open dist/whisperninja.app"
echo "   macOS will prompt for permissions on first run"