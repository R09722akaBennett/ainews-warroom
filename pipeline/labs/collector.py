"""Lab news collector: Google News and official X posts per lab."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx
from rich.console import Console

from labs.config import LABS
from labs.x_source import fetch_x_items

console = Console()

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.fromisoformat(raw).astimezone(timezone.utc)
        except Exception:
            return None


def _fetch_google_news(query: str, cutoff: datetime) -> list[dict]:
    """Fetch from Google News RSS for a specific query."""
    items: list[dict] = []
    try:
        url = f"{GOOGLE_NEWS_RSS}?q={query}&hl=en-US&gl=US&ceid=US:en"
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            pub_date = _parse_date(entry.get("published"))
            if pub_date and pub_date < cutoff:
                continue

            title = entry.get("title", "")
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1].strip()

            link = entry.get("link", "")
            if not link:
                continue

            items.append({
                "title": title,
                "url": link,
                "source": source,
                "published_at": pub_date.isoformat() if pub_date else None,
                "content": entry.get("summary", "")[:500],
            })
    except Exception as e:
        console.print(f"    [red]Google News error: {e}[/]")

    return items



def fetch_company_news(company_key: str, hours: int = 72) -> list[dict]:
    """Fetch news for a single company from all configured sources."""
    config = LABS.get(company_key)
    if not config:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_items: list[dict] = []

    # Google News
    for query in config.get("google_queries", []):
        items = _fetch_google_news(query, cutoff)
        all_items.extend(items)


    # Deduplicate by URL
    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_items:
        key = item["url"].split("?")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 3-day age filter (same as main collector)
    max_age = timedelta(days=3)
    age_cutoff = datetime.now(timezone.utc) - max_age
    filtered = []
    for item in unique:
        pub = item.get("published_at")
        if pub:
            try:
                dt = datetime.fromisoformat(pub)
                if dt < age_cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        filtered.append(item)

    return filtered


def collect_all_competitors() -> dict[str, list[dict]]:
    """Fetch news for all competitors. Returns {company_key: [items]}."""
    result: dict[str, list[dict]] = {}

    for key, config in LABS.items():
        console.print(f"    {config['name']}...", end=" ")
        items = fetch_company_news(key)
        result[key] = items
        console.print(f"[green]{len(items)} items[/]")

    for key, posts in fetch_x_items().items():
        result.setdefault(key, []).extend(posts)

    return result
