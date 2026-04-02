#!/usr/bin/env python3
"""Standalone fetch module for vibereader-menubar.

Fully self-contained — no external dependencies beyond feedparser and aiohttp.
Fetches from Hacker News API + RSS feeds, tags by category, scores by relevance.

Usage as a module:
    from fetch import run_fetch
    await run_fetch()

Usage as a script:
    python3 fetch.py
"""
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

try:
    import feedparser
    _FEEDPARSER = True
except ImportError:
    _FEEDPARSER = False

try:
    import aiohttp
    _AIOHTTP = True
except ImportError:
    _AIOHTTP = False


ARTICLES_PATH = os.path.expanduser("~/.vibereader/articles.json")
PREFERENCES_PATH = os.path.expanduser("~/.vibereader/preferences.json")

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

SOURCE_FEEDS = {
    'hn': None,
    'hnrss': 'https://hnrss.org/newest?points=100',
    'techcrunch': 'https://techcrunch.com/feed/',
    'theverge': 'https://www.theverge.com/rss/index.xml',
    'arstechnica': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
    'wired': 'https://www.wired.com/feed/rss',
    'techmeme': 'https://www.techmeme.com/feed.xml',
    'slashdot': 'https://rss.slashdot.org/Slashdot/slashdotMain',
    'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss',
    'cointelegraph': 'https://cointelegraph.com/rss',
    'newscientist': 'https://www.newscientist.com/section/news/feed/',
    'quanta': 'https://www.quantamagazine.org/feed/',
    'sciencedaily': 'https://www.sciencedaily.com/rss/top.xml',
    'producthunt': 'https://www.producthunt.com/feed',
    'reddit-prog': 'https://www.reddit.com/r/programming/.rss',
}

LEGACY_SOURCE_MAP = {
    'rss-google': ['techcrunch', 'theverge', 'wired'],
    'rss-hnrss': ['hnrss'],
}

CATEGORY_KEYWORDS = {
    'ai-ml': ['ai', 'llm', 'gpt', 'machine learning', 'neural', 'openai', 'anthropic', 'model', 'ml', 'deep learning', 'transformer', 'claude', 'gemini'],
    'web-dev': ['javascript', 'react', 'css', 'frontend', 'node', 'typescript', 'browser', 'web', 'html', 'vue', 'svelte', 'nextjs'],
    'systems': ['linux', 'kernel', 'rust', 'c++', 'os', 'infrastructure', 'distributed', 'database', 'postgres', 'redis'],
    'crypto': ['crypto', 'blockchain', 'bitcoin', 'ethereum', 'web3', 'defi', 'nft', 'token'],
    'science': ['research', 'paper', 'study', 'physics', 'biology', 'math', 'climate', 'space', 'nasa'],
    'devtools': ['git', 'ide', 'vscode', 'editor', 'cli', 'terminal', 'docker', 'kubernetes', 'ci/cd', 'devtool'],
    'security': ['security', 'vulnerability', 'hack', 'exploit', 'privacy', 'encryption', 'malware', 'cve'],
    'open-source': ['open source', 'github', 'oss', 'foss', 'mit license', 'apache', 'contributor'],
}


@dataclass
class Article:
    id: str
    title: str
    url: str
    source: str
    author: str
    score: float
    fetched_at: str
    summary: str = ''


# ── Fetchers (inline, no external package needed) ─────────────


async def fetch_hn(limit=20):
    """Fetch top stories from Hacker News. Falls back to HNRSS on any failure."""
    # Try HN API via aiohttp first
    if _AIOHTTP:
        try:
            articles = []
            async with aiohttp.ClientSession() as session:
                async with session.get(HN_TOP_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    ids = await resp.json()
                tasks = [_fetch_hn_item(session, i) for i in ids[:limit]]
                results = await asyncio.gather(*tasks)
                articles = [a for a in results if a]
            if articles:
                return articles
        except Exception as e:
            print(f"[vibe] HN API failed ({e}), falling back to HNRSS", file=sys.stderr)
    # Fallback: HNRSS feed via feedparser (works without aiohttp)
    return await fetch_rss('https://hnrss.org/newest?points=50', limit=limit)


async def _fetch_hn_item(session, item_id):
    try:
        async with session.get(HN_ITEM_URL.format(item_id), timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
        if not data or data.get('type') != 'story':
            return None
        return Article(
            id=str(data.get('id', '')),
            title=data.get('title', ''),
            url=data.get('url', f"https://news.ycombinator.com/item?id={data.get('id', '')}"),
            source='HN',
            author=data.get('by', ''),
            score=data.get('score', 0),
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        return None


async def fetch_rss(url, limit=10):
    """Fetch articles from an RSS feed using feedparser."""
    if not _FEEDPARSER:
        return []
    articles = []
    try:
        raw = None
        if _AIOHTTP:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {'User-Agent': 'Vibereader/0.3 (+https://github.com/TT-Wang/vibereader)'}
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), headers=headers) as resp:
                        raw = await resp.text()
            except Exception:
                raw = None
        if raw is None:
            # Sync fallback — feedparser can fetch URLs directly
            loop = asyncio.get_running_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)
        else:
            feed = feedparser.parse(raw)

        if feed.get('bozo') and not feed.get('entries'):
            print(f"[vibe] RSS parse failed ({url[:40]}): {feed.get('bozo_exception', 'unknown')}", file=sys.stderr)
            return []

        now = datetime.now(timezone.utc).isoformat()
        for entry in feed.get('entries', [])[:limit]:
            link = entry.get('link', '')
            if not link:
                continue
            summary_raw = entry.get('summary', '') or entry.get('description', '')
            summary_clean = re.sub(r'<[^>]+>', '', summary_raw).strip()
            if len(summary_clean) > 150:
                summary_clean = summary_clean[:150] + '...'
            articles.append(Article(
                id=link,
                title=entry.get('title', ''),
                url=link,
                source=feed.get('feed', {}).get('title', url[:30]),
                author=entry.get('author', ''),
                score=0,
                fetched_at=now,
                summary=summary_clean,
            ))
    except Exception as e:
        print(f"[vibe] RSS fetch failed ({url[:40]}): {e}", file=sys.stderr)
    return articles


# ── Helpers ────────────────────────────────────────────────────


def load_preferences():
    if not os.path.exists(PREFERENCES_PATH):
        return None
    try:
        with open(PREFERENCES_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def tag_article(title, url):
    text = (title + ' ' + url).lower()
    matched = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched.append(category)
                break
    return matched


def score_article(article_dict, prefs):
    base = min(article_dict.get('score', 0) / 100, 1.0)
    fetched_at = article_dict.get('fetched_at', '')
    recency = 0.0
    if fetched_at:
        try:
            if isinstance(fetched_at, str):
                if fetched_at.endswith('Z'):
                    fetched_dt = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                else:
                    fetched_dt = datetime.fromisoformat(fetched_at)
                    if fetched_dt.tzinfo is None:
                        fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
            else:
                fetched_dt = fetched_at
                if fetched_dt.tzinfo is None:
                    fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - fetched_dt).total_seconds()
            if age_seconds < 3600:
                recency = 1.0
            elif age_seconds < 21600:
                recency = 0.5
        except Exception:
            pass
    pref_bonus = 0.0
    if prefs is not None:
        preferred = set(prefs.get('categories', []))
        matched = set(article_dict.get('categories', []))
        pref_bonus = min(len(preferred & matched) * 0.5, 1.0)
    return base + recency + pref_bonus


# ── Main fetch orchestrator ───────────────────────────────────


async def run_fetch() -> None:
    """Fetch articles from all configured sources and save to ~/.vibereader/articles.json."""
    if not _FEEDPARSER and not _AIOHTTP:
        print("[vibe] No fetch libraries. Run: pip3 install feedparser aiohttp", file=sys.stderr)
        return
    if not _AIOHTTP:
        print("[vibe] aiohttp not installed — HN API disabled, using RSS feeds only", file=sys.stderr)
    if not _FEEDPARSER:
        print("[vibe] feedparser not installed — RSS feeds disabled, using HN API only", file=sys.stderr)

    prefs = load_preferences()

    # Resolve active sources
    if prefs and prefs.get('sources'):
        active = set()
        for s in prefs['sources']:
            if s in LEGACY_SOURCE_MAP:
                active.update(LEGACY_SOURCE_MAP[s])
            elif s in SOURCE_FEEDS:
                active.add(s)
        if not active:
            active = set(SOURCE_FEEDS.keys())
    else:
        active = set(SOURCE_FEEDS.keys())

    tasks = []
    if 'hn' in active:
        tasks.append(fetch_hn(limit=20))
    for name, url in SOURCE_FEEDS.items():
        if name == 'hn' or url is None:
            continue
        if name in active:
            tasks.append(fetch_rss(url, limit=10))

    results = await asyncio.gather(*tasks)

    seen = set()
    articles = []
    for batch in results:
        for a in batch:
            if a.id not in seen:
                seen.add(a.id)
                articles.append(a)

    serialized = []
    for a in articles:
        d = asdict(a)
        d['categories'] = tag_article(d.get('title', ''), d.get('url', ''))
        d['score'] = score_article(d, prefs)
        serialized.append(d)

    serialized.sort(key=lambda d: d['score'], reverse=True)

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(serialized),
        "articles": serialized[:50],
    }

    os.makedirs(os.path.dirname(ARTICLES_PATH), exist_ok=True)
    tmp = ARTICLES_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, ARTICLES_PATH)

    print(f"Saved {len(serialized)} articles to {ARTICLES_PATH}")


if __name__ == "__main__":
    asyncio.run(run_fetch())
