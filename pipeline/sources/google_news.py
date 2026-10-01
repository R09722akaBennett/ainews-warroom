"""Fetch AI news from Google News RSS search (public feeds, no auth)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from models import NewsItem, SourceType
from config import GOOGLE_NEWS_QUERIES

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def fetch_google_news(hours: int = 48) -> list[NewsItem]:
    """Fetch AI news from Google News RSS search."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[NewsItem] = []

    for query in GOOGLE_NEWS_QUERIES:
        try:
            url = f"{GOOGLE_NEWS_RSS}?q={query}&hl=en-US&gl=US&ceid=US:en"
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                pub_date = None
                raw_date = entry.get("published")
                if raw_date:
                    try:
                        pub_date = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
                    except Exception:
                        pass

                if pub_date and pub_date < cutoff:
                    continue

                link = entry.get("link", "")
                if not link:
                    continue

                # Google News titles often have " - Source" suffix
                title = entry.get("title", "")
                original_source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    original_source = parts[1].strip()

                items.append(NewsItem(
                    title=title,
                    url=link,
                    source_type=SourceType.GOOGLE_NEWS,
                    source_name="Google News",
                    content=entry.get("summary", "")[:3000],
                    published_at=pub_date,
                    metadata={"query": query[:50], "via": original_source},
                ))

        except Exception as e:
            print(f"[Google News] Error: {e}")

    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.url.split("?")[0]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique
