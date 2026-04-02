#!/usr/bin/env bash
# One-liner install for Vibereader Menu Bar
# Usage: curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash
set -e

INSTALL_DIR="$HOME/vibereader-menubar"
BIN_DIR="/usr/local/bin"

echo "🐷 Installing Vibereader Menu Bar..."

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
  echo "  Updating existing install..."
  cd "$INSTALL_DIR" && git pull -q
else
  echo "  Cloning repo..."
  git clone -q https://github.com/TT-Wang/vibereader-menubar.git "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# Python deps
echo "  Installing Python dependencies..."
pip3 install -q vibereader feedparser aiohttp 2>/dev/null

# Build
echo "  Building (swift build)..."
swift build -q 2>/dev/null

# Install binary
echo "  Installing to $BIN_DIR..."
sudo mkdir -p "$BIN_DIR"
sudo cp .build/debug/VibereaderMenuBar "$BIN_DIR/"

echo ""
echo "🐷 Done! Run with:"
echo "   VibereaderMenuBar"
echo ""
echo "   To launch at login: System Settings > General > Login Items > add VibereaderMenuBar"
