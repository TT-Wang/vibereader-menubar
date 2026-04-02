#!/usr/bin/env python3
"""Vibereader — native macOS menu bar app for curated tech news."""
import json
import os
import sys
import asyncio
import threading
import time
import webbrowser

# Ensure we can import fetch.py from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rumps

from fetch import run_fetch

ARTICLES_PATH = os.path.expanduser("~/.vibereader/articles.json")
PREFS_PATH = os.path.expanduser("~/.vibereader/preferences.json")
TITLE_MAX = 55
TOP_N = 15


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


def filter_articles(articles, prefs):
    cats = set(prefs.get("categories", []))
    if cats:
        filtered = [a for a in articles if set(a.get("categories", [])) & cats]
        if len(filtered) >= 5:
            articles = filtered
    articles.sort(key=lambda a: a.get("score", 0), reverse=True)
    return articles[:TOP_N]


def do_fetch():
    """Run fetch in a background thread."""
    threading.Thread(target=lambda: asyncio.run(run_fetch()), daemon=True).start()


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


CAT_ICONS = {
    'ai-ml': '🤖', 'web-dev': '🌐', 'systems': '⚙️', 'security': '🔒',
    'crypto': '⛓️', 'science': '🔬', 'devtools': '🔧', 'open-source': '📦',
}


class VibereaderApp(rumps.App):
    def __init__(self):
        super().__init__("🐷", quit_button=None)
        self.menu = ["Loading..."]
        # Initial fetch
        do_fetch()
        # Refresh menu every 30 seconds
        self.timer = rumps.Timer(self.refresh_menu, 30)
        self.timer.start()
        # Fetch new articles every 5 minutes
        self.fetch_timer = rumps.Timer(self.auto_fetch, 300)
        self.fetch_timer.start()
        # Build menu after a short delay for first fetch
        threading.Timer(3, self.refresh_menu, args=[None]).start()

    def refresh_menu(self, _):
        data = load_articles()
        prefs = load_prefs()
        articles = filter_articles(data.get("articles", []), prefs)
        fetched = age_str(data.get("fetched_at"))

        self.menu.clear()

        if not articles:
            self.menu.add(rumps.MenuItem("No articles yet — fetching..."))
        else:
            header = f"📰 {len(articles)} articles"
            if fetched:
                header += f" ({fetched})"
            self.menu.add(rumps.MenuItem(header))
            self.menu.add(rumps.separator)

            for a in articles:
                title = a.get("title", "")
                if len(title) > TITLE_MAX:
                    title = title[:TITLE_MAX - 3] + "..."
                cats = a.get("categories", [])
                icon = ""
                for c in cats:
                    if c in CAT_ICONS:
                        icon = CAT_ICONS[c] + " "
                        break
                url = a.get("url", "")
                item = rumps.MenuItem(f"{icon}{title}", callback=lambda _, u=url: webbrowser.open(u))
                self.menu.add(item)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("🔄 Refresh", callback=lambda _: do_fetch()))
        self.menu.add(rumps.MenuItem("🌐 Open Dashboard", callback=lambda _: webbrowser.open("http://localhost:8888")))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=lambda _: rumps.quit_application()))

    def auto_fetch(self, _):
        do_fetch()


def start_backend():
    """Start the web backend in background."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vibereader_web.py")
    if os.path.exists(script):
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    return None


if __name__ == "__main__":
    backend = start_backend()
    try:
        VibereaderApp().run()
    finally:
        if backend:
            backend.terminate()
