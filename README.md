# Vibereader

Curated tech news dashboard. One command to install, one command to run.

## Install

```bash
curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash && source ~/.zshrc && vibereader
```

That's it. Opens `http://localhost:8888` with your personalized news feed.

## What You Get

- Live headlines from **Hacker News, TechCrunch, Wired, Ars Technica**, and 11 more sources
- Articles scored by popularity + recency
- Category tags (AI/ML, web dev, crypto, science, security, etc.)
- One-click to read any article
- Refresh button for instant updates
- Works alongside the [Claude Code plugin](https://github.com/TT-Wang/vibereader) if you use it

## Commands

```bash
vibereader          # Start the dashboard
Ctrl+C              # Stop
```

## Troubleshooting

**`vibereader: command not found`** — Run `source ~/.zshrc` or restart your terminal.

**`pip install failed`** — Run manually: `python3 -m pip install --user feedparser aiohttp`

**Page shows no articles** — Wait a few seconds for the first fetch to complete, then click Refresh.

## Requirements

- Python 3.9+
- That's it. The install script handles everything else.

## Also Available: Claude Code Plugin

If you use [Claude Code](https://claude.com/claude-code), install the companion plugin for articles pushed directly in your terminal while you code:

```bash
claude plugin add github:TT-Wang/vibereader
```

## License

MIT
