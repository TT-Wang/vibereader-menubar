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
curl -sL "$BASE/vibereader_web.py" -o "$DIR/vibereader_web.py"

# Install Python deps
echo "  Installing dependencies..."
if ! python3 -c "import feedparser" 2>/dev/null; then
  python3 -m pip install feedparser aiohttp 2>/dev/null \
    || python3 -m pip install --user feedparser aiohttp 2>/dev/null \
    || python3 -m pip install --break-system-packages feedparser aiohttp 2>/dev/null \
    || echo "  ⚠️  pip failed. Run: python3 -m pip install --user feedparser aiohttp"
fi

# Verify at least feedparser works
if ! python3 -c "import feedparser" 2>/dev/null; then
  echo "  ⚠️  feedparser not found. Run: python3 -m pip install --user feedparser"
  exit 1
fi
echo "  ✓ Dependencies OK"

# Create single launcher
cat > "$BIN_DIR/vibereader" <<'LAUNCHER'
#!/usr/bin/env bash
# Kill any existing vibereader backend
pkill -f "vibereader_web.py" 2>/dev/null || true

cd "$HOME/.vibereader-app"
python3 vibereader_web.py &
PID=$!
sleep 1
open "http://localhost:8888" 2>/dev/null || xdg-open "http://localhost:8888" 2>/dev/null || true
echo "🐷 Vibereader running — http://localhost:8888 (pid $PID)"
echo "   Press Ctrl+C to stop."
trap "kill $PID 2>/dev/null" EXIT
wait $PID
LAUNCHER
chmod +x "$BIN_DIR/vibereader"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  SHELL_RC=""
  [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
  [ -z "$SHELL_RC" ] && [ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"
  [ -z "$SHELL_RC" ] && [ -f "$HOME/.bash_profile" ] && SHELL_RC="$HOME/.bash_profile"

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
echo "   If not found, run: source ~/.zshrc"
