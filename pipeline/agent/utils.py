"""Agent utility functions."""

from __future__ import annotations

from models import NewsItem


def deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    """Remove duplicate items by URL."""
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = item.relevance_key()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
