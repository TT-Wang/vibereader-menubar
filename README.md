# Vibereader

Curated tech news in your macOS menu bar. 🐷

## Install

```bash
curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader-menubar/main/install.sh | bash && source ~/.zshrc
```

## Run

```bash
vibereader
```

A 🐷 appears in your menu bar. Click it → headlines. Click a headline → opens in browser. That's it.

## Features

- 🐷 native macOS menu bar icon
- 15 news sources (HN, TechCrunch, Wired, Ars Technica, CoinDesk, Quanta, and more)
- Articles scored by popularity + recency
- Category icons (🤖 AI, 🌐 web, ⚙️ systems, 🔒 security, 🔬 science)
- Auto-refreshes every 5 minutes
- Runs locally — no server, no account, no signup

## Troubleshooting

| Problem | Fix |
|---|---|
| `command not found` | `source ~/.zshrc` or restart terminal |
| No articles | Wait a few seconds, click 🔄 Refresh |
| pip failed | `python3 -m pip install --user feedparser aiohttp rumps` |

## Requirements

- macOS
- Python 3.9+

## License

MIT
