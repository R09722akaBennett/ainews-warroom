"""Warroom track — KDAN-focused compression from daily digests."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console

from db.digests import load_daily_digests
from db.summaries import save_summary, load_summaries, get_latest_summary
from compress.dates import last_week_range, last_month_range, last_quarter_range
from compress.llm import compress_with_llm
from prompts import build_warroom_compress_prompt

console = Console()

# Period constants
WEEKLY = "weekly"
MONTHLY = "monthly"
QUARTERLY = "quarterly"


def run_weekly(ref_date: datetime):
    start, end = last_week_range(ref_date)
    console.print(f"\n[bold]🏢 Warroom weekly: {start} ~ {end}[/]\n")

    digests = load_daily_digests(start, end)
    if not digests:
        console.print("[yellow]No daily digests found. Skipping.[/]")
        return

    console.print(f"  Found {len(digests)} daily digests")
    parts = [f"### {d['date']} — {d['title']}\n{d['insights']}\n" for d in digests]
    source_text = "\n---\n".join(parts)

    prev = get_latest_summary(WEEKLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_warroom_compress_prompt(source_text, "weekly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(WEEKLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")


def run_monthly(ref_date: datetime):
    start, end = last_month_range(ref_date)
    console.print(f"\n[bold]🏢 Warroom monthly: {start} ~ {end}[/]\n")

    weeklies = load_summaries(WEEKLY, start, end)
    if weeklies:
        console.print(f"  Found {len(weeklies)} weekly summaries")
        parts = [f"### 週報 {w['start_date']} ~ {w['end_date']} — {w['title']}\n{w['content']}\n" for w in weeklies]
        source_text = "\n---\n".join(parts)
    else:
        console.print("  [dim]No weekly summaries, using daily digests[/]")
        digests = load_daily_digests(start, end)
        if not digests:
            console.print("[yellow]No data found. Skipping.[/]")
            return
        console.print(f"  Found {len(digests)} daily digests")
        parts = [f"### {d['date']} — {d['title']}\n{d['insights']}\n" for d in digests]
        source_text = "\n---\n".join(parts)

    prev = get_latest_summary(MONTHLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_warroom_compress_prompt(source_text, "monthly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(MONTHLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")


def run_quarterly(ref_date: datetime):
    start, end = last_quarter_range(ref_date)
    console.print(f"\n[bold]🏢 Warroom quarterly: {start} ~ {end}[/]\n")

    monthlies = load_summaries(MONTHLY, start, end)
    if monthlies:
        console.print(f"  Found {len(monthlies)} monthly summaries")
        parts = [f"### 月報 {m['start_date']} ~ {m['end_date']} — {m['title']}\n{m['content']}\n" for m in monthlies]
        source_text = "\n---\n".join(parts)
    else:
        weeklies = load_summaries(WEEKLY, start, end)
        if weeklies:
            console.print(f"  [dim]No monthly summaries, using {len(weeklies)} weekly summaries[/]")
            parts = [f"### 週報 {w['start_date']} ~ {w['end_date']} — {w['title']}\n{w['content']}\n" for w in weeklies]
            source_text = "\n---\n".join(parts)
        else:
            digests = load_daily_digests(start, end)
            if not digests:
                console.print("[yellow]No data found. Skipping.[/]")
                return
            console.print(f"  [dim]Using {len(digests)} daily digests[/]")
            parts = [f"### {d['date']} — {d['title']}\n{d['insights']}\n" for d in digests]
            source_text = "\n---\n".join(parts)

    prev = get_latest_summary(QUARTERLY)
    prev_dict = {"start_date": prev.start_date, "end_date": prev.end_date, "content": prev.content} if prev else None
    prompt = build_warroom_compress_prompt(source_text, "quarterly", start, end, previous_summary=prev_dict)
    title, content, tags, token_usage = compress_with_llm(prompt)
    if token_usage:
        console.print(f"  Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")
    save_summary(QUARTERLY, start, end, title, content, tags, token_usage)
    console.print(f"  [green]✓[/] Saved: {title}")
