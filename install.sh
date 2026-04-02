#!/usr/bin/env bash
# Vibereader — one-liner install
# curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash
set -e

DIR="$HOME/.vibereader-app"
BIN_DIR="$HOME/.local/bin"
BASE="https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main"

echo "🐷 Installing Vibereader..."

mkdir -p "$DIR" "$BIN_DIR"

# Download
echo "  Downloading..."
curl -sL "$BASE/fetch.py" -o "$DIR/fetch.py"
curl -sL "$BASE/vibereader_menubar.py" -o "$DIR/vibereader_menubar.py"

# Install Python deps
echo "  Installing dependencies..."
if ! python3 -c "import feedparser, rumps" 2>/dev/null; then
  python3 -m pip install feedparser aiohttp rumps 2>/dev/null \
    || python3 -m pip install --user feedparser aiohttp rumps 2>/dev/null \
    || python3 -m pip install --break-system-packages feedparser aiohttp rumps 2>/dev/null \
    || { echo "  ⚠️  Run manually: python3 -m pip install --user feedparser aiohttp rumps"; exit 1; }
fi

if ! python3 -c "import feedparser, rumps" 2>/dev/null; then
  echo "  ⚠️  Missing deps. Run: python3 -m pip install --user feedparser aiohttp rumps"
  exit 1
fi
echo "  ✓ OK"

# Create launcher
cat > "$BIN_DIR/vibereader" <<'LAUNCHER'
#!/usr/bin/env bash
pkill -f "vibereader_menubar.py" 2>/dev/null || true
cd "$HOME/.vibereader-app"
exec python3 vibereader_menubar.py
LAUNCHER
chmod +x "$BIN_DIR/vibereader"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  SHELL_RC=""
  [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
  [ -z "$SHELL_RC" ] && [ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"

  if [ -n "$SHELL_RC" ] && ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "  Added ~/.local/bin to PATH in $(basename "$SHELL_RC")"
  fi
  export PATH="$BIN_DIR:$PATH"
fi

echo ""
echo "🐷 Done! Run:"
echo "   vibereader"
echo ""
echo "   A 🐷 appears in your menu bar. Click it to read."
echo "   If not found: source ~/.zshrc"
