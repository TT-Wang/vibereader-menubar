#!/usr/bin/env bash
# Vibereader — one-liner install
# curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash
set -e

DIR="$HOME/.vibereader-app"
BIN_DIR="$HOME/.local/bin"
BASE="https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main"

# Find best Python (prefer 3.12/3.13 over 3.14+ which breaks rumps)
PY=""
for candidate in python3.12 python3.13 python3.11 python3; do
  if command -v "$candidate" &>/dev/null; then
    PY="$candidate"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "❌ Python 3 not found. Install from https://python.org"
  exit 1
fi

echo "🐷 Installing Vibereader (using $PY)..."

mkdir -p "$DIR" "$BIN_DIR"

# Download
echo "  Downloading..."
curl -sL "$BASE/fetch.py" -o "$DIR/fetch.py"
curl -sL "$BASE/vibereader_menubar.py" -o "$DIR/vibereader_menubar.py"

# Install Python deps
echo "  Installing dependencies..."
if ! "$PY" -c "import feedparser, rumps" 2>/dev/null; then
  "$PY" -m pip install feedparser aiohttp rumps 2>/dev/null \
    || "$PY" -m pip install --user feedparser aiohttp rumps 2>/dev/null \
    || "$PY" -m pip install --break-system-packages feedparser aiohttp rumps 2>/dev/null \
    || { echo "  ⚠️  Run manually: $PY -m pip install --user feedparser aiohttp rumps"; exit 1; }
fi

if ! "$PY" -c "import feedparser, rumps" 2>/dev/null; then
  echo "  ⚠️  Missing deps. Run: $PY -m pip install --user feedparser aiohttp rumps"
  exit 1
fi
echo "  ✓ OK"

# Create launcher with the detected Python
cat > "$BIN_DIR/vibereader" <<LAUNCHER
#!/usr/bin/env bash
pkill -f "vibereader_menubar.py" 2>/dev/null || true
cd "\$HOME/.vibereader-app"
exec $PY vibereader_menubar.py
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
