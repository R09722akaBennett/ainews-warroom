"""
Lobsters source — fetches AI/ML tagged stories from lobste.rs.
No auth required, uses public JSON API.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import httpx

from models import NewsItem, SourceType
from config import LOBSTERS_AI_TAGS

LOBSTERS_API = "https://lobste.rs"


def fetch_lobsters(hours: int = 48) -> list[NewsItem]:
    """Fetch recent AI/ML stories from Lobsters."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[NewsItem] = []

    for tag in LOBSTERS_AI_TAGS:
        try:
            resp = httpx.get(
                f"{LOBSTERS_API}/t/{tag}.json",
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
            stories = resp.json()

            for story in stories:
                pub_date = None
                if story.get("created_at"):
                    try:
                        pub_date = datetime.fromisoformat(
                            story["created_at"].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                if pub_date and pub_date < cutoff:
                    continue

                url = story.get("url") or story.get("short_id_url", "")
                if not url:
                    continue

                items.append(NewsItem(
                    title=story.get("title", ""),
                    url=url,
                    source_type=SourceType.LOBSTERS,
                    source_name="Lobsters",
                    content=story.get("description", "")[:500],
                    score=story.get("score", 0),
                    comments_count=story.get("comment_count", 0),
                    published_at=pub_date,
                    metadata={"tags": story.get("tags", [])},
                ))

        except Exception as e:
            print(f"[Lobsters] Error fetching tag={tag}: {e}")

    # Deduplicate (same story can have multiple tags)
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        if item.url not in seen:
            seen.add(item.url)
            unique.append(item)

    unique.sort(key=lambda x: x.score, reverse=True)
    return unique
