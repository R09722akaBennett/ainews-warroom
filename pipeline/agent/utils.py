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


def filter_seen_urls(items: list[NewsItem], seen_urls: set[str]) -> tuple[list[NewsItem], int]:
    """Filter out items whose URL appeared in recent days. Returns (filtered, removed_count)."""
    filtered = []
    removed = 0
    for item in items:
        if item.relevance_key() in seen_urls:
            removed += 1
        else:
            filtered.append(item)
    return filtered, removed
