"""
Product Hunt source — fetches trending AI products.
Uses the public RSS feed (no auth required).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from models import NewsItem, SourceType

PRODUCTHUNT_FEED = "https://www.producthunt.com/feed"

AI_KEYWORDS = [
    "ai", "llm", "gpt", "machine learning", "deep learning", "neural",
    "chatbot", "copilot", "agent", "automation", "nlp", "computer vision",
    "generative", "diffusion", "transformer", "embedding", "vector",
    "rag", "fine-tune", "inference", "model", "prompt",
]


def fetch_producthunt(hours: int = 48) -> list[NewsItem]:
    """Fetch AI-related products from Product Hunt RSS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[NewsItem] = []

    try:
        resp = httpx.get(PRODUCTHUNT_FEED, timeout=15, follow_redirects=True)
        feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            pub_date = None
            raw_date = entry.get("published")
            if raw_date:
                try:
                    pub_date = parsedate_to_datetime(raw_date).astimezone(timezone.utc)
                except Exception:
                    try:
                        pub_date = datetime.fromisoformat(raw_date).astimezone(timezone.utc)
                    except Exception:
                        pass

            if pub_date and pub_date < cutoff:
                continue

            title = entry.get("title", "")
            summary = entry.get("summary", "")
            combined = f"{title} {summary}".lower()

            # Filter for AI-related products
            if not any(kw in combined for kw in AI_KEYWORDS):
                continue

            link = entry.get("link", "")
            if not link:
                continue

            items.append(NewsItem(
                title=title,
                url=link,
                source_type=SourceType.PRODUCTHUNT,
                source_name="Product Hunt",
                content=summary[:3000],
                published_at=pub_date,
                metadata={},
            ))

    except Exception as e:
        print(f"[Product Hunt] Error: {e}")

    return items
