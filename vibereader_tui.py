#!/usr/bin/env python3
"""Vibereader TUI — rich terminal news reader for tmux."""
import json
import os
import sys
import asyncio
import threading
import time
import select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.console import Console, Group
from rich.rule import Rule

from fetch import run_fetch, SOURCE_FEEDS

ARTICLES_PATH = os.path.expanduser("~/.vibereader/articles.json")
PREFS_PATH = os.path.expanduser("~/.vibereader/preferences.json")
ACTIVITY_PATH = os.path.expanduser("~/.vibereader/activity-state.json")
PAGE_SIZE = 3

CAT_ICONS = {
    'ai-ml': '🤖',
    'web-dev': '🌐',
    'systems': '⚙️',
    'security': '🔒',
    'crypto': '⛓️',
    'science': '🔬',
    'devtools': '🔧',
    'open-source': '📦',
}

DEFAULT_ICON = '📰'


class State:
    """Shared mutable state between threads."""
    def __init__(self):
        self.lock = threading.Lock()
        self.page_offset = 0
        self.quit = False
        self.force_refresh = False
        self.fetching = False


def load_articles():
    """Load articles from the articles JSON file."""
    try:
        with open(ARTICLES_PATH) as f:
            return json.load(f)
    except Exception:
        return {"articles": [], "fetched_at": None}


def load_prefs():
    """Load user preferences."""
    try:
        with open(PREFS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def load_activity():
    """Read activity-state.json written by Claude Code plugin PostToolUse hook."""
    try:
        with open(ACTIVITY_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def filter_articles(articles, prefs):
    """Filter and return articles, optionally filtered by preferred categories."""
    if not prefs:
        return articles
    preferred = set(prefs.get('categories', []))
    if not preferred:
        return articles
    # Return preferred-category articles first, then others
    pref_articles = [a for a in articles if set(a.get('categories', [])) & preferred]
    other_articles = [a for a in articles if not (set(a.get('categories', [])) & preferred)]
    return pref_articles + other_articles


def age_str(iso):
    """Return a human-readable age string for an ISO timestamp."""
    if not iso:
        return 'unknown'
    try:
        from datetime import datetime, timezone
        if iso.endswith('Z'):
            iso = iso.replace('Z', '+00:00')
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        if age < 60:
            return 'just now'
        elif age < 3600:
            mins = int(age / 60)
            return f'{mins}m ago'
        elif age < 86400:
            hrs = int(age / 3600)
            return f'{hrs}h ago'
        else:
            days = int(age / 86400)
            return f'{days}d ago'
    except Exception:
        return '?'


def is_claude_active():
    """Check if Claude Code is actively working (tool call within 120s)."""
    try:
        with open(ACTIVITY_PATH) as f:
            state = json.load(f)
        return (time.time() - state.get('last_tool_call_ts', 0)) < 120
    except Exception:
        return False


def get_article_icon(article):
    """Get the best icon for an article based on its categories."""
    cats = article.get('categories', [])
    for cat in cats:
        if cat in CAT_ICONS:
            return CAT_ICONS[cat]
    return DEFAULT_ICON


def wrap_text(text, width, indent=3):
    """Wrap text to the given width with an indent for continuation lines."""
    if not text:
        return []
    words = text.split()
    lines = []
    current_line = ''
    first_line = True
    effective_width = width - indent - 2  # account for borders and spacing

    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= effective_width:
            current_line += ' ' + word
        else:
            lines.append(current_line)
            current_line = word
            first_line = False

    if current_line:
        lines.append(current_line)

    return lines


def build_display(articles, state, total, fetched_at, claude_active, term_width):
    """Build a rich renderable for the current view."""
    renderables = []

    # ── Header panel ──────────────────────────────────────────────
    header_text = Text()
    header_text.append("🐷 Vibereader", style="bold cyan")
    header_text.append("  ")

    article_count = total if total else 0
    header_text.append(f"{article_count} articles", style="cyan")
    header_text.append(" · ", style="dim")
    header_text.append(f"fetched {age_str(fetched_at)}", style="dim")

    if state.fetching:
        header_text.append("  ⟳ fetching...", style="yellow")

    header_text.append("\n")

    if claude_active:
        header_text.append("🟢 Claude is working", style="bold green")
        header_text.append(" — auto-pushing", style="green")
    else:
        header_text.append("🔴 Claude idle", style="dim red")

    header_panel = Panel(header_text, style="cyan", padding=(0, 1))
    renderables.append(header_panel)
    renderables.append(Text(""))  # spacer

    # ── Articles ──────────────────────────────────────────────────
    if not articles:
        no_articles = Text("  No articles available. Press r to refresh.", style="dim")
        renderables.append(no_articles)
    else:
        for i, article in enumerate(articles):
            icon = get_article_icon(article)
            title = article.get('title', 'Untitled')
            summary = article.get('summary', '')
            source = article.get('source', '')
            score = article.get('score', 0)
            categories = article.get('categories', [])

            # Title line: icon + bold title
            title_text = Text()
            title_text.append(f" {icon}  ", style="")
            title_text.append(title, style="bold white")
            renderables.append(title_text)

            # Summary lines with vertical bar prefix
            if summary:
                summary_lines = wrap_text(summary, term_width)
                for line in summary_lines:
                    line_text = Text()
                    line_text.append(" ┃  ", style="dim cyan")
                    line_text.append(line, style="dim")
                    renderables.append(line_text)

            # Metadata line
            meta_text = Text()
            meta_text.append(" ┃  ", style="dim cyan")
            meta_str_parts = []
            if source:
                meta_str_parts.append(source)
            if score:
                meta_str_parts.append(f"⭐ {score:.1f}")
            if categories:
                meta_str_parts.append(', '.join(categories[:2]))
            meta_text.append('── ' + ' · '.join(meta_str_parts) + ' ', style="dim")
            # Fill remaining width with dashes
            meta_content_len = 4 + 3 + sum(len(p) + 3 for p in meta_str_parts)
            fill = max(0, term_width - meta_content_len - 4)
            if fill > 0:
                meta_text.append('─' * min(fill, 20), style="dim")
            renderables.append(meta_text)

            # Spacer between articles
            if i < len(articles) - 1:
                renderables.append(Text(""))

    renderables.append(Text(""))  # spacer before footer

    # ── Footer panel ──────────────────────────────────────────────
    with state.lock:
        offset = state.page_offset

    start = offset + 1
    end = min(offset + PAGE_SIZE, total) if total else 0

    footer_text = Text()
    footer_text.append(f"📄 {start}-{end} of {total}", style="dim")
    footer_text.append("\n")
    footer_text.append("n", style="bold cyan")
    footer_text.append(":next  ", style="dim")
    footer_text.append("p", style="bold cyan")
    footer_text.append(":prev  ", style="dim")
    footer_text.append("r", style="bold cyan")
    footer_text.append(":refresh  ", style="dim")
    footer_text.append("q", style="bold cyan")
    footer_text.append(":quit", style="dim")

    footer_panel = Panel(footer_text, style="dim", padding=(0, 1))
    renderables.append(footer_panel)

    return Group(*renderables)


def kb_listener(state):
    """Listen for keyboard input in raw mode."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while not state.quit:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)
                with state.lock:
                    if ch == 'q':
                        state.quit = True
                    elif ch == 'n':
                        state.page_offset += PAGE_SIZE
                    elif ch == 'p':
                        state.page_offset -= PAGE_SIZE
                    elif ch == 'r':
                        state.force_refresh = True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


SOURCE_GROUPS = {
    '📰 News': ['hn', 'hnrss', 'techmeme', 'slashdot'],
    '💻 Tech': ['techcrunch', 'theverge', 'arstechnica', 'wired'],
    '₿ Crypto': ['coindesk', 'cointelegraph'],
    '🔬 Science': ['newscientist', 'quanta', 'sciencedaily'],
    '🚀 Other': ['producthunt', 'reddit-prog'],
}

SOURCE_LABELS = {
    'hn': 'Hacker News', 'hnrss': 'HN RSS (100+ pts)', 'techcrunch': 'TechCrunch',
    'theverge': 'The Verge', 'arstechnica': 'Ars Technica', 'wired': 'Wired',
    'techmeme': 'Techmeme', 'slashdot': 'Slashdot', 'coindesk': 'CoinDesk',
    'cointelegraph': 'Cointelegraph', 'newscientist': 'New Scientist',
    'quanta': 'Quanta Magazine', 'sciencedaily': 'Science Daily',
    'producthunt': 'Product Hunt', 'reddit-prog': 'Reddit /r/programming',
}

CATEGORY_LABELS = {
    'ai-ml': 'AI & Machine Learning', 'web-dev': 'Web Development',
    'systems': 'Systems & Infrastructure', 'crypto': 'Crypto & Blockchain',
    'science': 'Science & Research', 'devtools': 'Developer Tools',
    'security': 'Security & Privacy', 'open-source': 'Open Source',
}


def run_onboarding():
    """Interactive first-run setup. Lets user pick sources and categories."""
    console = Console()

    console.print()
    console.print(Panel(
        Text.from_markup("[bold cyan]🐷 Welcome to Vibereader![/]\n\nLet's set up your news feed."),
        style="cyan", padding=(1, 2),
    ))
    console.print()

    # ── Step 1: Pick sources ──────────────────────────────────
    console.print("[bold]Step 1:[/] Which news sources do you want?\n")

    all_keys = []
    idx = 1
    for group, keys in SOURCE_GROUPS.items():
        console.print(f"  [bold]{group}[/]")
        for key in keys:
            label = SOURCE_LABELS.get(key, key)
            console.print(f"    [cyan]{idx:2}[/]. {label}")
            all_keys.append(key)
            idx += 1
        console.print()

    console.print(f"  [dim]Enter numbers separated by commas, or[/] [bold]a[/] [dim]for all.[/]")
    choice = console.input("\n  [bold cyan]Sources >[/] ").strip()

    if choice.lower() == 'a' or choice == '':
        selected_sources = list(SOURCE_FEEDS.keys())
        console.print("  [green]✓ All sources selected[/]\n")
    else:
        selected_sources = []
        for part in choice.replace(' ', '').split(','):
            try:
                n = int(part)
                if 1 <= n <= len(all_keys):
                    selected_sources.append(all_keys[n - 1])
            except ValueError:
                if part in SOURCE_FEEDS:
                    selected_sources.append(part)
        if not selected_sources:
            selected_sources = list(SOURCE_FEEDS.keys())
            console.print("  [yellow]No valid selection — using all sources[/]\n")
        else:
            names = ', '.join(SOURCE_LABELS.get(s, s) for s in selected_sources)
            console.print(f"  [green]✓ Selected: {names}[/]\n")

    # ── Step 2: Pick categories ───────────────────────────────
    console.print("[bold]Step 2:[/] Which topics interest you?\n")

    cat_keys = list(CATEGORY_LABELS.keys())
    for i, (key, label) in enumerate(CATEGORY_LABELS.items(), 1):
        icon = CAT_ICONS.get(key, '📰')
        console.print(f"    [cyan]{i:2}[/]. {icon} {label}")

    console.print(f"\n  [dim]Enter numbers separated by commas, or[/] [bold]a[/] [dim]for all.[/]")
    choice = console.input("\n  [bold cyan]Categories >[/] ").strip()

    if choice.lower() == 'a' or choice == '':
        selected_cats = cat_keys[:]
        console.print("  [green]✓ All categories selected[/]\n")
    else:
        selected_cats = []
        for part in choice.replace(' ', '').split(','):
            try:
                n = int(part)
                if 1 <= n <= len(cat_keys):
                    selected_cats.append(cat_keys[n - 1])
            except ValueError:
                if part in CATEGORY_LABELS:
                    selected_cats.append(part)
        if not selected_cats:
            selected_cats = cat_keys[:]
            console.print("  [yellow]No valid selection — using all categories[/]\n")
        else:
            names = ', '.join(CATEGORY_LABELS.get(c, c) for c in selected_cats)
            console.print(f"  [green]✓ Selected: {names}[/]\n")

    # ── Save preferences ──────────────────────────────────────
    prefs = load_prefs()
    prefs['sources'] = selected_sources
    prefs['categories'] = selected_cats

    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    tmp = PREFS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(prefs, f, indent=2)
    os.replace(tmp, PREFS_PATH)

    console.print(Panel(
        Text.from_markup("[bold green]✓ Preferences saved![/]\n\nFetching your first articles..."),
        style="green", padding=(0, 2),
    ))
    console.print()

    # Do initial fetch synchronously so articles are ready
    try:
        asyncio.run(run_fetch())
    except Exception:
        pass


def main():
    # Run onboarding if no preferences exist
    if not os.path.exists(PREFS_PATH):
        run_onboarding()

    state = State()

    # Initial fetch in background
    def _initial_fetch():
        try:
            asyncio.run(run_fetch())
        except Exception as e:
            pass  # silently ignore errors during initial fetch

    threading.Thread(target=_initial_fetch, daemon=True).start()

    # Start keyboard listener
    kb = threading.Thread(target=kb_listener, args=(state,), daemon=True)
    kb.start()

    console = Console()
    last_fetch = time.time()
    last_auto_push = time.time()

    with Live(console=console, refresh_per_second=2, screen=True) as live:
        while not state.quit:
            now = time.time()

            # Check Claude activity
            claude_active = is_claude_active()

            # Auto-push when Claude is working (every 20s)
            if claude_active and (now - last_auto_push) > 20:
                with state.lock:
                    state.page_offset += PAGE_SIZE
                last_auto_push = now

            # Auto-fetch every 5 min
            if (now - last_fetch) > 300:
                if not state.fetching:
                    state.fetching = True

                    def _bg_fetch():
                        try:
                            asyncio.run(run_fetch())
                        except Exception:
                            pass
                        state.fetching = False

                    threading.Thread(target=_bg_fetch, daemon=True).start()
                    last_fetch = now

            # Force refresh
            if state.force_refresh:
                state.force_refresh = False
                if not state.fetching:
                    state.fetching = True

                    def _force_fetch():
                        try:
                            asyncio.run(run_fetch())
                        except Exception:
                            pass
                        state.fetching = False

                    threading.Thread(target=_force_fetch, daemon=True).start()
                    last_fetch = now

            # Load and filter articles
            data = load_articles()
            prefs = load_prefs()
            all_articles = filter_articles(data.get("articles", []), prefs)
            total = len(all_articles)

            with state.lock:
                if total > 0:
                    state.page_offset = state.page_offset % total
                    # Ensure non-negative after modulo (handles negative values)
                    state.page_offset = (state.page_offset % total + total) % total
                offset = state.page_offset

            page = all_articles[offset:offset + PAGE_SIZE]

            display = build_display(
                page,
                state,
                total,
                data.get("fetched_at"),
                claude_active,
                console.width or 80,
            )
            live.update(display)

            time.sleep(0.5)


if __name__ == "__main__":
    main()
