"""
Hacker News source — fetches top stories and filters for AI-related content.
Uses the official HN Firebase API (free, no auth needed).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from models import NewsItem, SourceType
from config import HACKERNEWS_TOP_N, HACKERNEWS_AI_KEYWORDS

HN_API = "https://hacker-news.firebaseio.com/v0"


async def _fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    try:
        resp = await client.get(f"{HN_API}/item/{item_id}.json", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _is_ai_related(item: dict) -> bool:
    """Check if a HN story is AI-related based on title keywords."""
    title = (item.get("title") or "").lower()
    text = (item.get("text") or "").lower()
    combined = f"{title} {text}"
    return any(kw in combined for kw in HACKERNEWS_AI_KEYWORDS)


async def fetch_hackernews() -> list[NewsItem]:
    """Fetch top AI-related stories from Hacker News."""
    async with httpx.AsyncClient() as client:
        # Get top story IDs
        resp = await client.get(f"{HN_API}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:HACKERNEWS_TOP_N]

        # Fetch all stories concurrently
        tasks = [_fetch_item(client, sid) for sid in story_ids]
        stories = await asyncio.gather(*tasks)

        items: list[NewsItem] = []
        for story in stories:
            if story is None or story.get("type") != "story":
                continue
            if not _is_ai_related(story):
                continue

            items.append(NewsItem(
                title=story.get("title", ""),
                url=story.get("url", f"https://news.ycombinator.com/item?id={story['id']}"),
                source_type=SourceType.HACKERNEWS,
                source_name="Hacker News",
                content=story.get("text", ""),
                score=story.get("score", 0),
                comments_count=story.get("descendants", 0),
                published_at=datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc),
                metadata={"hn_id": story["id"]},
            ))

        items.sort(key=lambda x: x.score, reverse=True)
        return items
