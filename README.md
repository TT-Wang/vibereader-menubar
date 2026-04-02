# Vibereader Menu Bar

Native macOS menu bar app for curated tech news. Standalone — works with or without the [Claude Code plugin](https://github.com/TT-Wang/vibereader).

![macOS 13+](https://img.shields.io/badge/macOS-13%2B-blue) ![Swift 5.9](https://img.shields.io/badge/Swift-5.9-orange)

## Install

```bash
curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash
```

Then run:
```bash
VibereaderMenuBar
```

That's it. The script clones, installs deps, builds, and puts the binary in your PATH. The app auto-starts its Python backend — no separate server to run.

## Features

- **Menu bar popover** — click "V" in your menu bar for a SwiftUI panel (no Dock icon)
- **Live headlines** — top 15 articles with colored score badges, category pills, and source labels
- **Search/filter** — live search bar to filter articles by text
- **Click to read** — opens articles in your default browser
- **Auto-refresh** — fetches new articles every 60 seconds
- **Refresh Feed** — manual refresh button with spinning indicator
- **Claude Code status** — menu bar icon turns green when Claude is actively working
- **Auto-start backend** — Python web server starts/stops with the app

## How It Works

```
┌───────────────────────────┐
│   VibereaderMenuBar.app   │  SwiftUI menu bar popover
│   (Swift / AppKit)        │
└─────────┬─────────────────┘
          │ HTTP (localhost:8888)
          ▼
┌───────────────────────────┐
│   vibereader_web.py       │  Python HTTP backend (auto-started)
│   /api/articles           │  → reads ~/.vibereader/articles.json
│   /api/status             │  → reads ~/.vibereader/activity-state.json
│   /refresh                │  → triggers fetch.py
└─────────┬─────────────────┘
          │ imports
          ▼
┌───────────────────────────┐
│   fetch.py                │  Standalone fetch module
│   run_fetch()             │  HN API + 14 RSS feeds
│                           │  → writes ~/.vibereader/articles.json
└───────────────────────────┘
```

### Standalone Architecture

The menubar app has its **own fetch logic** (`fetch.py`) and does NOT depend on the Claude Code plugin. Both products share data via `~/.vibereader/`:

- If the plugin is also installed, they complement each other — the plugin keeps articles fresh while you code, and the menubar gives you a visual browser
- If only the menubar is installed, it fetches articles on its own

## Requirements

- macOS 13 (Ventura) or later
- Swift 5.9+ (Xcode 15+)
- Python 3.11+
- Python packages: `vibereader`, `feedparser`, `aiohttp`

```bash
pip install vibereader feedparser aiohttp
```

## Configuration

### API Backend

The backend runs on `localhost:8888` by default. Override with:

```bash
export VIBEREADER_API=http://your-server:8888
.build/debug/VibereaderMenuBar
```

### News Preferences

The app reads `~/.vibereader/preferences.json` if it exists:

```json
{
  "categories": ["ai-ml", "crypto", "science"],
  "sources": ["hn", "techcrunch", "coindesk", "quanta"],
  "style": "summaries"
}
```

Create this file manually or use the Claude Code plugin's `/vibe-setup` wizard.

## API Contract

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/api/articles` | `{"articles": [...], "fetched_at": "ISO8601"}` |
| GET | `/api/status` | `{"claude_active": bool, "idle_seconds": int, ...}` |
| POST | `/refresh` | `{"status": "ok"}` |

## System Tray (Alternative)

A Python-based system tray app is also included for non-macOS or lightweight use:

```bash
pip install -r requirements-tray.txt
python3 vibereader_tray.py
```

## Web Dashboard

The backend also serves a web dashboard at `http://localhost:8888`:

```bash
python3 vibereader_web.py
# Open http://localhost:8888 in your browser
```

## Launch at Login

```bash
swift build -c release
cp .build/release/VibereaderMenuBar /usr/local/bin/
```

Then add `/usr/local/bin/VibereaderMenuBar` to System Settings > General > Login Items.

## Project Structure

```
vibereader-menubar/
├── Package.swift                              # SPM manifest
├── Sources/VibereaderMenuBar/
│   ├── main.swift                             # App entry point
│   ├── AppDelegate.swift                      # Menu bar + backend lifecycle
│   ├── Config.swift                           # API URL config
│   ├── Models/
│   │   ├── Article.swift                      # Article model
│   │   └── ClaudeStatus.swift                 # Claude activity model
│   ├── Services/
│   │   ├── ArticleService.swift               # Article API client
│   │   ├── StatusService.swift                # Status API client
│   │   └── NotificationManager.swift          # macOS notifications
│   ├── ViewModels/
│   │   └── AppState.swift                     # Observable state
│   └── Views/
│       ├── PopoverContentView.swift           # Main popover UI
│       └── ArticleRowView.swift               # Article row component
├── fetch.py                                   # Standalone fetch module
├── vibereader_web.py                          # HTTP backend + web dashboard
├── vibereader_tray.py                         # System tray alternative
└── requirements-tray.txt                      # Python dependencies for tray
```

## See Also

- **[Vibereader Plugin](https://github.com/TT-Wang/vibereader)** — Claude Code plugin that pushes curated articles while you code

## License

MIT
