"""Industry track — unfiltered AI industry compression from raw items."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from rich.console import Console

from db.raw_items import get_raw_items
from db.summaries import save_summary, load_summaries, get_latest_summary
from compress.dates import last_week_range, last_month_range, last_quarter_range
from compress.llm import compress_with_llm
from prompts import build_industry_compress_prompt

console = Console()

# Period constants
RAW_WEEKLY = "raw_weekly"
RAW_MONTHLY = "raw_monthly"
RAW_QUARTERLY = "raw_quarterly"


def _raw_items_to_text(items: list[dict]) -> str:
    """Convert raw items into compact text grouped by date and source."""
    by_date: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_date[it["date"]].append(it)

    parts = []
    for date in sorted(by_date.keys()):
        day_items = by_date[date]
        lines = [f"### {date} ({len(day_items)} items)"]
        by_source: dict[str, list[str]] = defaultdict(list)
        for it in day_items:
            by_source[it["source"]].append(it["title"])
        for source in sorted(by_source.keys()):
            titles = by_source[source]
            lines.append(f"**{source}** ({len(titles)}):")
            for t in titles:
                lines.append(f"- {t}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def run_raw_weekly(ref_date: datetime):
    start, end = last_week_range(ref_date)
    console.print(f"\n[bold]🌐 Industry weekly: {start} ~ {end}[/]\n")

    items = get_raw_items(start, end)
    if not items:
        console.print("[yellow]No raw items found. Skipping.[/]")
        return

    console.print(f"  Found {len(items)} raw items")
    source_text = _raw_items_to_text(items)

    prev = get_latest_summary(RAW_WEEKLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_industry_compress_prompt(source_text, "weekly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(RAW_WEEKLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")


def run_raw_monthly(ref_date: datetime):
    start, end = last_month_range(ref_date)
    console.print(f"\n[bold]🌐 Industry monthly: {start} ~ {end}[/]\n")

    weeklies = load_summaries(RAW_WEEKLY, start, end)
    if weeklies:
        console.print(f"  Found {len(weeklies)} raw weekly summaries")
        parts = [
            f"### 產業週報 {w['start_date']} ~ {w['end_date']} — {w['title']}\n{w['content']}\n"
            for w in weeklies
        ]
        source_text = "\n---\n".join(parts)
    else:
        console.print("  [dim]No raw weekly summaries, using raw items directly[/]")
        items = get_raw_items(start, end)
        if not items:
            console.print("[yellow]No data found. Skipping.[/]")
            return
        console.print(f"  Found {len(items)} raw items")
        source_text = _raw_items_to_text(items)

    prev = get_latest_summary(RAW_MONTHLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_industry_compress_prompt(source_text, "monthly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(RAW_MONTHLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")


def run_raw_quarterly(ref_date: datetime):
    start, end = last_quarter_range(ref_date)
    console.print(f"\n[bold]🌐 Industry quarterly: {start} ~ {end}[/]\n")

    monthlies = load_summaries(RAW_MONTHLY, start, end)
    if monthlies:
        console.print(f"  Found {len(monthlies)} raw monthly summaries")
        parts = [
            f"### 產業月報 {m['start_date']} ~ {m['end_date']} — {m['title']}\n{m['content']}\n"
            for m in monthlies
        ]
        source_text = "\n---\n".join(parts)
    else:
        weeklies = load_summaries(RAW_WEEKLY, start, end)
        if weeklies:
            console.print(f"  [dim]No raw monthly summaries, using {len(weeklies)} raw weekly summaries[/]")
            parts = [
                f"### 產業週報 {w['start_date']} ~ {w['end_date']} — {w['title']}\n{w['content']}\n"
                for w in weeklies
            ]
            source_text = "\n---\n".join(parts)
        else:
            items = get_raw_items(start, end)
            if not items:
                console.print("[yellow]No data found. Skipping.[/]")
                return
            console.print(f"  [dim]Using {len(items)} raw items directly[/]")
            source_text = _raw_items_to_text(items)

    prev = get_latest_summary(RAW_QUARTERLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_industry_compress_prompt(source_text, "quarterly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(RAW_QUARTERLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")
