"""News collection — gathers from all sources and deduplicates."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

from rich.console import Console

from models import NewsItem
from sources.hackernews import fetch_hackernews
from sources.reddit import fetch_reddit
from sources.rss_feeds import fetch_rss_feeds
from sources.lobsters import fetch_lobsters
from sources.google_news import fetch_google_news
from agent.utils import deduplicate, filter_seen_urls
from agent.raw_exporter import export_raw_markdown
from db import save_raw_items, get_recent_urls

console = Console()


async def collect_news(date: str) -> tuple[list[NewsItem], int]:
    """Collect AI news from all sources, deduplicate, save raw, return sorted items."""
    all_items: list[NewsItem] = []

    # Async source
    hn_items = await fetch_hackernews()
    all_items.extend(hn_items)
    console.print(f"    HN: {len(hn_items)}")

    # Sync sources — run in parallel via thread pool
    loop = asyncio.get_event_loop()
    sources = [
        ("Reddit", fetch_reddit),
        ("RSS", fetch_rss_feeds),
        ("Lobsters", fetch_lobsters),
        ("Google News", fetch_google_news),
    ]

    tasks = [loop.run_in_executor(None, fn) for _, fn in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (name, _), result in zip(sources, results):
        if isinstance(result, Exception):
            console.print(f"    [red]{name}: error — {result}[/]")
        else:
            all_items.extend(result)
            console.print(f"    {name}: {len(result)}")

    all_items = deduplicate(all_items)
    console.print(f"    Total (deduped): {len(all_items)}")

    # Cross-day dedup: remove URLs already seen in past 7 days
    seen_urls = get_recent_urls(date, days=7)
    if seen_urls:
        all_items, removed = filter_seen_urls(all_items, seen_urls)
        if removed:
            console.print(f"    [yellow]Filtered {removed} items seen in past 7 days[/]")
        console.print(f"    Total (cross-day deduped): {len(all_items)}")

    # Filter out items older than 3 days (keep items with no date)
    max_age = timedelta(days=3)
    cutoff = datetime.now(timezone.utc) - max_age
    before = len(all_items)
    all_items = [
        it for it in all_items
        if it.published_at is None or it.published_at >= cutoff
    ]
    aged_out = before - len(all_items)
    if aged_out:
        console.print(f"    [yellow]Filtered {aged_out} items older than 3 days[/]")
        console.print(f"    Total (age-filtered): {len(all_items)}")

    # Save raw items as markdown audit trail + condensed to DB
    raw_path = export_raw_markdown(all_items, date)
    save_raw_items(date, [
        {"title": i.title, "url": i.url, "source": i.source_name, "score": i.score}
        for i in all_items
    ])
    console.print(f"  [green]✓[/] Raw: {len(all_items)} items → {raw_path}")

    total_count = len(all_items)
    console.print(f"  [green]✓[/] {total_count} items ready for report")

    return all_items, total_count
