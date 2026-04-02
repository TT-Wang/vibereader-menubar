#!/usr/bin/env bash
# Vibereader — one-liner install
# curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash
set -e

DIR="$HOME/.vibereader-app"
BASE="https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main"

echo "🐷 Installing Vibereader..."

mkdir -p "$DIR"

# Download the two Python files
echo "  Downloading..."
curl -sL "$BASE/fetch.py" -o "$DIR/fetch.py"
curl -sL "$BASE/vibereader_web.py" -o "$DIR/vibereader_web.py"

# Install Python deps
echo "  Installing dependencies..."
pip3 install -q vibereader feedparser aiohttp 2>/dev/null

# Create launcher script
cat > "$DIR/vibereader" <<'LAUNCHER'
#!/usr/bin/env bash
cd "$HOME/.vibereader-app"
python3 vibereader_web.py &
PID=$!
sleep 1
open "http://localhost:8888" 2>/dev/null || echo "Open http://localhost:8888 in your browser"
echo "🐷 Vibereader running (pid $PID). Press Ctrl+C to stop."
trap "kill $PID 2>/dev/null" EXIT
wait $PID
LAUNCHER
chmod +x "$DIR/vibereader"

# Symlink to PATH
ln -sf "$DIR/vibereader" /usr/local/bin/vibereader 2>/dev/null || {
  echo "  Run: sudo ln -sf $DIR/vibereader /usr/local/bin/vibereader"
}

echo ""
echo "🐷 Done! Run:"
echo "   vibereader"
