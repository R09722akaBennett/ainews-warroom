"""Lab news collector: the labs' official X posts.

Google News was dropped on 2026-10-01. It brought about 750 media items a day,
mostly finance and aggregator sites mentioning a lab in passing, and the
labs' own posts are the first-hand signal the Labs page is about.
"""

from __future__ import annotations

from labs.x_source import fetch_x_items


def collect_all_competitors() -> dict[str, list[dict]]:
    """Return {lab_key: [items]} of the official posts published since the last read."""
    return fetch_x_items()
