# Vibereader

Curated tech news in your macOS menu bar. One command.

## Install

```bash
curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash && source ~/.zshrc
```

## Run

```bash
vibereader
```

A 🐷 icon appears in your menu bar. Click it to browse headlines. That's it.

## What You Get

- 🐷 pig icon in your menu bar — click to see headlines
- 15 sources (HN, TechCrunch, Wired, Ars Technica, CoinDesk, Quanta, and more)
- Articles scored by popularity + recency
- Category icons (🤖 AI, 🌐 web, ⚙️ systems, 🔒 security, 🔬 science, etc.)
- Click any headline to open in browser
- Auto-refreshes every 5 minutes
- Web dashboard also available at http://localhost:8888

## Troubleshooting

| Problem | Fix |
|---|---|
| `vibereader: command not found` | `source ~/.zshrc` or restart terminal |
| No articles in menu | Wait a few seconds, click 🔄 Refresh |
| `pip install failed` | `python3 -m pip install --user feedparser aiohttp rumps` |

## Also: Claude Code Plugin

Get articles pushed in your terminal while Claude works:

```bash
claude plugin add github:TT-Wang/vibereader
```

## License

MIT
