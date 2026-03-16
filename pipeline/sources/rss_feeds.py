"""
RSS source — fetches recent entries from a curated list of AI blogs and newsletters.
Only returns items published within the last 24 hours.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from models import NewsItem, SourceType
from config import RSS_FEEDS


def _parse_date(entry: dict) -> datetime | None:
    """Try to extract a datetime from a feed entry."""
    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            except Exception:
                try:
                    return datetime.fromisoformat(raw).astimezone(timezone.utc)
                except Exception:
                    pass
    # feedparser's parsed struct
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_content(entry: dict) -> str:
    """Extract the best available content/summary from a feed entry."""
    # Try content first
    if entry.get("content"):
        return entry["content"][0].get("value", "")[:5000]
    # Then summary
    if entry.get("summary"):
        return entry["summary"][:5000]
    # Then description
    if entry.get("description"):
        return entry["description"][:5000]
    return ""


def fetch_rss_feeds(hours: int = 24) -> list[NewsItem]:
    """Fetch recent items from all configured RSS feeds."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[NewsItem] = []

    for feed_name, feed_url in RSS_FEEDS.items():
        try:
            # Use httpx for timeout control, then parse
            resp = httpx.get(feed_url, timeout=15, follow_redirects=True)
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                pub_date = _parse_date(entry)

                # Skip old entries
                if pub_date and pub_date < cutoff:
                    continue

                link = entry.get("link", "")
                if not link:
                    continue

                items.append(NewsItem(
                    title=entry.get("title", "Untitled"),
                    url=link,
                    source_type=SourceType.RSS,
                    source_name=feed_name,
                    content=_extract_content(entry),
                    published_at=pub_date,
                    metadata={"feed": feed_name},
                ))

        except Exception as e:
            print(f"[RSS] Error fetching {feed_name}: {e}")

    return items
