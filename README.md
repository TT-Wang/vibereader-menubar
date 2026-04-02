# Vibereader

Curated tech news in your terminal. Runs alongside Claude Code in tmux. 🐷

## Install

```bash
curl -sL https://raw.githubusercontent.com/TT-Wang/vibereader/main/install.sh | bash && source ~/.zshrc
```

## Run

```bash
vibereader
```

First run asks you to pick your sources and categories. Then the TUI launches.

### tmux Split (recommended)

```bash
# Pane 1: Claude Code
claude

# Ctrl+b then % to split vertically

# Pane 2: Vibereader
vibereader
```

While Claude works, vibereader detects the activity and auto-pushes new articles.

## Features

- 🐷 rich terminal UI — runs in any terminal or tmux pane
- **Onboarding** — pick from 15 sources and 8 categories on first run
- **3 articles at a time** with AI summaries
- **Auto-push** — detects Claude Code activity, rotates articles while Claude works
- **Keyboard controls** — `n` next, `p` prev, `r` refresh, `q` quit
- **Auto-fetch** every 5 minutes
- Also available as macOS menu bar: `vibereader --menubar`

## Sources (pick during setup)

| Group | Sources |
|---|---|
| 📰 News | Hacker News, HN RSS, Techmeme, Slashdot |
| 💻 Tech | TechCrunch, The Verge, Ars Technica, Wired |
| ₿ Crypto | CoinDesk, Cointelegraph |
| 🔬 Science | New Scientist, Quanta Magazine, Science Daily |
| 🚀 Other | Product Hunt, Reddit /r/programming |

## Categories

🤖 AI/ML · 🌐 Web Dev · ⚙️ Systems · 🔒 Security · ⛓️ Crypto · 🔬 Science · 🔧 DevTools · 📦 Open Source

## Troubleshooting

| Problem | Fix |
|---|---|
| `command not found` | `source ~/.zshrc` or restart terminal |
| SSL errors | `/Applications/Python\ 3.13/Install\ Certificates.command` |
| No articles | Wait a few seconds, press `r` to refresh |
| pip failed | `python3 -m pip install --user feedparser aiohttp rich` |

## Also: Claude Code Plugin

Get articles pushed inline while Claude works:

```bash
claude plugin add github:TT-Wang/vibereader-plugin
```

## License

MIT
