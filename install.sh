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
pip3 install -q feedparser aiohttp 2>/dev/null || pip install -q feedparser aiohttp 2>/dev/null

# Create launcher
cat > "$BIN_DIR/vibereader" <<'LAUNCHER'
#!/usr/bin/env bash
cd "$HOME/.vibereader-app"
python3 vibereader_web.py &
PID=$!
sleep 1
open "http://localhost:8888" 2>/dev/null || xdg-open "http://localhost:8888" 2>/dev/null || echo "Open http://localhost:8888"
echo "🐷 Vibereader running (pid $PID). Press Ctrl+C to stop."
trap "kill $PID 2>/dev/null" EXIT
wait $PID
LAUNCHER
chmod +x "$BIN_DIR/vibereader"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  SHELL_RC=""
  if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
  elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
  elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_RC="$HOME/.bash_profile"
  fi

  if [ -n "$SHELL_RC" ]; then
    if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
      echo "  Added ~/.local/bin to PATH in $(basename "$SHELL_RC")"
    fi
  fi
  export PATH="$BIN_DIR:$PATH"
fi

echo ""
echo "🐷 Done! Run:"
echo "   vibereader"
echo ""
echo "   If 'vibereader' is not found, restart your terminal or run:"
echo "   source ~/.zshrc"
