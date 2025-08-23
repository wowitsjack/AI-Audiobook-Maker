#!/bin/bash
# AI Audiobook Generator - Linux Installer
# Installs the application with desktop integration

set -e

APP_NAME="AI Audiobook Generator"
APP_ID="ai-audiobook-generator"
INSTALL_DIR="$HOME/.local/bin"
ICON_PATH="$HOME/.local/share/icons/$APP_ID.png"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_ID.desktop"

echo ""
echo "======================================"
echo "AI Audiobook Generator Installer"
echo "======================================"
echo ""

# Get the directory where this script is located (src directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if running from correct location
if [ ! -f "$PROJECT_ROOT/book.png" ] || [ ! -d "$SCRIPT_DIR" ]; then
    echo "ERROR: Please run this installer from the project root"
    echo "Usage: ./src/install.sh"
    exit 1
fi

echo "Installing AI Audiobook Generator..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$(dirname "$ICON_PATH")"
mkdir -p "$(dirname "$DESKTOP_FILE")"

# Create the main executable script
echo "Creating executable..."
cat > "$INSTALL_DIR/$APP_ID" << EOF
#!/bin/bash
# AI Audiobook Generator Launcher

# Get the directory where this script is located
APP_DIR="$HOME/.local/share/$APP_ID"

# Change to the application directory
cd "\$APP_DIR"

# Run the application
python3 audiobook_gui_launcher.py "\$@"
EOF

# Make executable
chmod +x "$INSTALL_DIR/$APP_ID"

# Install application files
APP_INSTALL_DIR="$HOME/.local/share/$APP_ID"
echo "Installing application files to $APP_INSTALL_DIR..."
mkdir -p "$APP_INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$APP_INSTALL_DIR/"
cp "$PROJECT_ROOT/README.md" "$APP_INSTALL_DIR/"

# Install icon
echo "Installing icon..."
cp "$PROJECT_ROOT/book.png" "$ICON_PATH"

# Create desktop file with exact same structure as existing
echo "Creating desktop entry..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AI Audiobook Generator
Comment=Generate professional audiobooks using Google's Gemini 2.5 Pro TTS
Exec=$INSTALL_DIR/$APP_ID
Icon=$ICON_PATH
Terminal=false
Categories=AudioVideo;Audio;Utility;
Keywords=audiobook;tts;text-to-speech;gemini;ai;book;narration;
StartupNotify=true
MimeType=text/plain;text/markdown;
EOF

# Make desktop file executable
chmod +x "$DESKTOP_FILE"

# Update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    echo "Updating desktop database..."
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "The AI Audiobook Generator has been installed to:"
echo "  Executable: $INSTALL_DIR/$APP_ID"
echo "  Icon: $ICON_PATH"
echo "  Desktop file: $DESKTOP_FILE"
echo ""
echo "You can now:"
echo "  • Find it in your applications menu"
echo "  • Run it from terminal: $APP_ID"
echo "  • Double-click the desktop file"
echo ""
echo "To uninstall, run: rm -f \"$INSTALL_DIR/$APP_ID\" \"$ICON_PATH\" \"$DESKTOP_FILE\" && rm -rf \"$APP_INSTALL_DIR\""
echo ""