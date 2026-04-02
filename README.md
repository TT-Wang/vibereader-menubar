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

A 🐷 appears in your menu bar. Click it → 3 curated headlines with AI summaries. That's it.

## Features

- 🐷 native macOS menu bar icon
- **3 articles at a time** with AI summaries below each headline
- **◀ ▶ page** through all articles, or **🔄 Refresh** to fetch new ones and advance
- **⚙️ Sources** — toggle 15 sources on/off directly from the menu (saves instantly)
- Auto-refreshes every 5 minutes
- Runs locally — no server, no account, no signup

## Sources (toggle in ⚙️ menu)

| Group | Sources |
|---|---|
| 📰 News | Hacker News, HN RSS, Techmeme, Slashdot |
| 💻 Tech | TechCrunch, The Verge, Ars Technica, Wired |
| ₿ Crypto | CoinDesk, Cointelegraph |
| 🔬 Science | New Scientist, Quanta Magazine, Science Daily |
| 🚀 Other | Product Hunt, Reddit /r/programming |

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
