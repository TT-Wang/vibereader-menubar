#!/usr/bin/env python3
"""Vibereader — native macOS menu bar app for curated tech news."""
import json
import os
import sys
import asyncio
import threading
import webbrowser

# Ensure we can import fetch.py from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rumps

from fetch import run_fetch, SOURCE_FEEDS

ARTICLES_PATH = os.path.expanduser("~/.vibereader/articles.json")
PREFS_PATH = os.path.expanduser("~/.vibereader/preferences.json")
TITLE_MAX = 55
PAGE_SIZE = 3

SOURCE_GROUPS = {
    '📰 News': ['hn', 'hnrss', 'techmeme', 'slashdot'],
    '💻 Tech': ['techcrunch', 'theverge', 'arstechnica', 'wired'],
    '₿ Crypto': ['coindesk', 'cointelegraph'],
    '🔬 Science': ['newscientist', 'quanta', 'sciencedaily'],
    '🚀 Other': ['producthunt', 'reddit-prog'],
}

SOURCE_LABELS = {
    'hn': 'Hacker News',
    'hnrss': 'HN RSS (100+ pts)',
    'techcrunch': 'TechCrunch',
    'theverge': 'The Verge',
    'arstechnica': 'Ars Technica',
    'wired': 'Wired',
    'techmeme': 'Techmeme',
    'slashdot': 'Slashdot',
    'coindesk': 'CoinDesk',
    'cointelegraph': 'Cointelegraph',
    'newscientist': 'New Scientist',
    'quanta': 'Quanta Magazine',
    'sciencedaily': 'Science Daily',
    'producthunt': 'Product Hunt',
    'reddit-prog': 'Reddit /r/programming',
}


def load_articles():
    try:
        with open(ARTICLES_PATH) as f:
            return json.load(f)
    except Exception:
        return {"fetched_at": None, "count": 0, "articles": []}


def load_prefs():
    try:
        with open(PREFS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_prefs(prefs):
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    tmp = PREFS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(prefs, f, indent=2)
    os.replace(tmp, PREFS_PATH)


def load_sources():
    """Return a set of enabled source keys. Defaults to all sources if no prefs."""
    prefs = load_prefs()
    if "sources" in prefs:
        return set(prefs["sources"])
    return set(SOURCE_FEEDS.keys())


def save_sources(enabled_set):
    prefs = load_prefs()
    prefs["sources"] = sorted(enabled_set)
    save_prefs(prefs)


def filter_articles(articles, prefs):
    cats = set(prefs.get("categories", []))
    if cats:
        filtered = [a for a in articles if set(a.get("categories", [])) & cats]
        if len(filtered) >= 5:
            articles = filtered
    articles.sort(key=lambda a: a.get("score", 0), reverse=True)
    return articles


def do_fetch(on_done=None):
    """Run fetch in a background thread, calling on_done() when complete."""
    def _run():
        asyncio.run(run_fetch())
        if on_done:
            on_done()
    threading.Thread(target=_run, daemon=True).start()


def age_str(iso):
    if not iso:
        return ""
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        mins = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins}m ago"
        return f"{mins // 60}h ago"
    except Exception:
        return ""


class VibereaderApp(rumps.App):
    def __init__(self):
        super().__init__("🐷", quit_button=None)
        self._page_offset = 0
        self.menu = ["Loading..."]
        do_fetch(on_done=lambda: self.refresh_menu(None))
        self.timer = rumps.Timer(self.refresh_menu, 30)
        self.timer.start()
        self.fetch_timer = rumps.Timer(self.auto_fetch, 300)
        self.fetch_timer.start()

    def refresh_menu(self, _):
        data = load_articles()
        prefs = load_prefs()
        all_articles = filter_articles(data.get("articles", []), prefs)
        fetched = age_str(data.get("fetched_at"))
        total = len(all_articles)

        # Clamp offset
        if total > 0:
            self._page_offset = self._page_offset % total
        else:
            self._page_offset = 0

        page_articles = all_articles[self._page_offset:self._page_offset + PAGE_SIZE]

        self.menu.clear()

        # Header
        header = f"📰 {total} articles"
        if fetched:
            header += f" ({fetched})"
        self.menu.add(rumps.MenuItem(header))

        # Page indicator
        if total > 0:
            start = self._page_offset + 1
            end = min(self._page_offset + PAGE_SIZE, total)
            self.menu.add(rumps.MenuItem(f"📄 {start}-{end} of {total}"))

        self.menu.add(rumps.separator)

        if not page_articles:
            self.menu.add(rumps.MenuItem("No articles yet — fetching..."))
        else:
            for a in page_articles:
                title = a.get("title", "")
                if len(title) > TITLE_MAX:
                    title = title[:TITLE_MAX - 3] + "..."
                url = a.get("url", "")
                summary = (a.get("summary") or "").strip()

                article_item = rumps.MenuItem(
                    f"🤖 {title}",
                    callback=lambda _, u=url: webbrowser.open(u),
                )
                self.menu.add(article_item)

                if summary:
                    summary_item = rumps.MenuItem(f"   {summary}")
                    self.menu.add(summary_item)

        self.menu.add(rumps.separator)

        # Paging buttons
        prev_item = rumps.MenuItem("◀ Previous", callback=self.prev_page)
        next_item = rumps.MenuItem("▶ Next", callback=self.next_page)
        self.menu.add(prev_item)
        self.menu.add(next_item)

        # Refresh button: fetch + advance page
        refresh_item = rumps.MenuItem("🔄 Refresh", callback=self.on_refresh)
        self.menu.add(refresh_item)

        self.menu.add(rumps.separator)

        # Sources submenu
        sources_item = rumps.MenuItem("⚙️ Sources")
        self.build_sources_submenu(sources_item)
        self.menu.add(sources_item)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=lambda _: rumps.quit_application()))

    def build_sources_submenu(self, parent_item):
        enabled = load_sources()
        for group_label, source_keys in SOURCE_GROUPS.items():
            header = rumps.MenuItem(group_label)
            parent_item.add(header)
            for key in source_keys:
                if key not in SOURCE_FEEDS:
                    continue
                label = SOURCE_LABELS.get(key, key)
                item = rumps.MenuItem(
                    label,
                    callback=lambda sender, k=key: self.toggle_source(sender, k),
                )
                item.state = 1 if key in enabled else 0
                parent_item.add(item)

    def toggle_source(self, sender, source_key):
        enabled = load_sources()
        if source_key in enabled:
            enabled.discard(source_key)
            sender.state = 0
        else:
            enabled.add(source_key)
            sender.state = 1
        save_sources(enabled)
        do_fetch(on_done=lambda: self.refresh_menu(None))

    def prev_page(self, _):
        data = load_articles()
        prefs = load_prefs()
        total = len(filter_articles(data.get("articles", []), prefs))
        if total > 0:
            self._page_offset = (self._page_offset - PAGE_SIZE) % total
        self.refresh_menu(None)

    def next_page(self, _):
        data = load_articles()
        prefs = load_prefs()
        total = len(filter_articles(data.get("articles", []), prefs))
        if total > 0:
            self._page_offset = (self._page_offset + PAGE_SIZE) % total
        self.refresh_menu(None)

    def on_refresh(self, _):
        data = load_articles()
        prefs = load_prefs()
        total = len(filter_articles(data.get("articles", []), prefs))
        if total > 0:
            self._page_offset = (self._page_offset + PAGE_SIZE) % total
        do_fetch(on_done=lambda: self.refresh_menu(None))

    def auto_fetch(self, _):
        do_fetch(on_done=lambda: self.refresh_menu(None))


if __name__ == "__main__":
    VibereaderApp().run()
