"""Competitor tracker — collect daily, classify weekly.

Usage:
    cd pipeline
    uv run python -m competitor                    # collect only (daily)
    uv run python -m competitor --classify         # collect + classify (weekly)
    uv run python -m competitor --date 2026-03-17
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from dotenv import load_dotenv
from rich.console import Console

from db import init_db, save_competitor_items, get_competitor_urls
from competitor.config import COMPETITORS
from competitor.collector import collect_all_competitors

console = Console()


def run_collect(date: str):
    """Daily: collect competitor news and save raw items to DB."""
    console.print(f"\n[bold]Competitor Tracker — Collect ({date})[/]\n")

    # Collect from all sources
    console.print("[bold]Collecting competitor news...[/]")
    all_news = collect_all_competitors()

    # Cross-day dedup
    seen_urls = get_competitor_urls(date, days=7)

    total = 0
    for company_key, items in all_news.items():
        # Filter out already-seen URLs
        if seen_urls:
            before = len(items)
            items = [it for it in items if it["url"].split("?")[0].rstrip("/") not in seen_urls]
            filtered = before - len(items)
            if filtered:
                console.print(f"    [yellow]{COMPETITORS[company_key]['name']}: filtered {filtered} seen items[/]")

        # Save to DB (unclassified — category="pending", ai_related=1)
        for item in items:
            item.setdefault("category", "pending")
            item.setdefault("ai_related", True)
            item.setdefault("summary", "")

        save_competitor_items(date, company_key, items)
        total += len(items)

    console.print(f"\n[bold green]Done! {total} items saved to DB[/]")
    return total


def run_classify(date: str):
    """Weekly: classify pending items with LLM."""
    from competitor.classifier import classify_batch

    console.print(f"\n[bold]Competitor Tracker — Classify ({date})[/]\n")

    # Get all pending items from the past 7 days
    from datetime import timedelta
    start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    from db.competitor_items import get_competitor_items as _get_items
    from db.connection import get_conn

    conn = get_conn()
    rows = conn.execute(
        "SELECT id, date, company, title, url, source, published_at, category, summary "
        "FROM competitor_items WHERE date >= ? AND date <= ? AND category = 'pending' "
        "ORDER BY company, date",
        (start, date),
    ).fetchall()
    conn.close()

    items_by_company: dict[str, list[dict]] = {}
    for r in rows:
        company = r["company"]
        items_by_company.setdefault(company, []).append(dict(r))

    total_tokens = {"input": 0, "output": 0, "total": 0}

    for company_key, items in items_by_company.items():
        config = COMPETITORS.get(company_key, {})
        name = config.get("name", company_key)
        from competitor.weekly import _describe
        domain = _describe(config)

        console.print(f"  Classifying [cyan]{name}[/] ({len(items)} items)...", end=" ")
        classified, token_usage = classify_batch(name, domain, items)

        if token_usage:
            for k in total_tokens:
                total_tokens[k] += token_usage.get(k, 0)

        # Update DB with classifications
        conn = get_conn()
        for item in classified:
            conn.execute(
                "UPDATE competitor_items SET category = ?, ai_related = ?, summary = ? WHERE id = ?",
                (item["category"], 1 if item["ai_related"] else 0, item["summary"], item["id"]),
            )
        conn.commit()
        conn.close()

        ai_count = sum(1 for i in classified if i["ai_related"])
        console.print(f"[green]{ai_count}/{len(classified)} AI-related[/]")

    if total_tokens["total"] > 0:
        console.print(f"\n  Classification tokens: input={total_tokens['input']:,} output={total_tokens['output']:,} total={total_tokens['total']:,}")

        # Save token usage for analytics tracking
        from db import save_summary
        save_summary(
            "labs_classify", date, date,
            f"Labs Classify ({date})",
            f"Classified {sum(len(v) for v in items_by_company.values())} items across {len(items_by_company)} companies",
            tags={"companies": list(items_by_company.keys())},
            token_usage=total_tokens,
        )

    console.print(f"\n[bold green]Classification done![/]")


def main():
    parser = argparse.ArgumentParser(description="Competitor Tracker")
    parser.add_argument("--classify", action="store_true", help="Run LLM classification (weekly)")
    parser.add_argument("--date", type=str, default=None, help="Override date (YYYY-MM-DD)")
    args = parser.parse_args()

    load_dotenv()
    init_db()

    today = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    run_collect(today)
    run_classify(today)

    if args.classify:
        # Weekly report (only on --classify flag, triggered on Mondays)
        from competitor.weekly import generate_weekly_report
        console.print(f"\n[bold]Generating competitor weekly report...[/]\n")
        generate_weekly_report(today)


if __name__ == "__main__":
    main()
