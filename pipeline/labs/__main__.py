"""Track the frontier labs: collect official X posts, classify them and write the daily brief.

Every run collects new posts, classifies the pending ones of the past 7 days
and writes that day's brief; --classify adds the weekly report (labs.sh
passes it on Mondays). Without --live the run only prints what it would do
and makes no network call, because a live run pays for X reads and Gemini.

Usage:
    cd pipeline
    uv run --no-sync python -m labs                    # dry-run
    uv run --no-sync python -m labs --live             # collect, classify, daily brief
    uv run --no-sync python -m labs --live --classify  # plus the weekly report
    uv run --no-sync python -m labs --live --date 2026-03-17
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import date as date_cls, datetime, timedelta, timezone

from rich.console import Console

from db import get_competitor_urls, init_db, save_competitor_items, save_summary
from db.connection import get_conn
from labs import x_source
from labs.config import LABS
from labs.knowledge import API as KNOWLEDGE_API, ingest_posts

console = Console()


def run_collect(date: str):
    """Save the labs' new X posts for date as pending items and send them to knowledge-api."""
    console.print(f"\n[bold]Labs tracker — collect ({date})[/]\n")
    all_news = x_source.fetch_x_items()
    seen_urls = get_competitor_urls(date, days=7)

    total = 0
    kb = {"created": 0, "skipped": 0, "failed": 0}
    for company_key, items in all_news.items():
        if seen_urls:
            before = len(items)
            items = [it for it in items if it["url"].split("?")[0].rstrip("/") not in seen_urls]
            filtered = before - len(items)
            if filtered:
                console.print(f"    [yellow]{LABS[company_key]['name']}: filtered {filtered} seen items[/]")

        for item in items:
            item.setdefault("category", "pending")
            item.setdefault("ai_related", True)
            item.setdefault("summary", "")

        save_competitor_items(date, company_key, items)
        k = ingest_posts(company_key, items)
        for key in kb:
            kb[key] += k[key]
        total += len(items)

    console.print(f"\n[bold green]Done! {total} items saved to DB[/]; knowledge DB {kb}")
    return total


def _classify_start(date: str, since: str | None) -> str:
    return since or (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def _pending_rows(start: str, end: str) -> list[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT id, date, company, title, url, source, published_at, category, summary, content "
            "FROM competitor_items WHERE date >= ? AND date <= ? AND category = 'pending' "
            "ORDER BY company, date",
            (start, end),
        ).fetchall()
    finally:
        conn.close()


def run_classify(date: str, since: str | None = None):
    """Classify the pending items from the 7 days before date, or from since when given.

    Items the model did not classify stay pending in the DB, so the next run
    picks them up again.
    """
    from labs.classifier import classify_batch
    from labs.weekly import _describe

    console.print(f"\n[bold]Labs tracker — classify ({date})[/]\n")
    items_by_company: dict[str, list[dict]] = {}
    for r in _pending_rows(_classify_start(date, since), date):
        items_by_company.setdefault(r["company"], []).append(dict(r))

    total_tokens = {"input": 0, "output": 0, "total": 0}
    for company_key, items in items_by_company.items():
        config = LABS.get(company_key, {})
        name = config.get("name", company_key)
        console.print(f"  Classifying [cyan]{name}[/] ({len(items)} items)...", end=" ")
        classified, token_usage = classify_batch(name, _describe(config), items)

        if token_usage:
            for k in total_tokens:
                total_tokens[k] += token_usage.get(k, 0)

        done = [i for i in classified if i["category"] != "pending"]
        conn = get_conn()
        for item in done:
            conn.execute(
                "UPDATE competitor_items SET category = ?, ai_related = ?, summary = ? WHERE id = ?",
                (item["category"], 1 if item["ai_related"] else 0, item["summary"], item["id"]),
            )
        conn.commit()
        conn.close()

        ai_count = sum(1 for i in done if i["ai_related"])
        left = len(classified) - len(done)
        console.print(f"[green]{ai_count}/{len(done)} AI-related[/]"
                      + (f", [yellow]{left} left pending[/]" if left else ""))

    if total_tokens["total"] > 0:
        console.print(f"\n  Classification tokens: input={total_tokens['input']:,} "
                      f"output={total_tokens['output']:,} total={total_tokens['total']:,}")
        # Recorded as a summary so the analytics page counts classification tokens.
        save_summary(
            "labs_classify", date, date,
            f"Labs Classify ({date})",
            f"Classified {sum(len(v) for v in items_by_company.values())} items "
            f"across {len(items_by_company)} companies",
            tags={"companies": list(items_by_company.keys())},
            token_usage=total_tokens,
        )

    console.print("\n[bold green]Classification done![/]")


def _count(sql: str, params: tuple) -> int:
    """Return a count from warroom.db, or 0 when the table does not exist yet."""
    try:
        conn = get_conn()
        try:
            return conn.execute(sql, params).fetchone()[0]
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return 0


def dry_run(today: str, classify_since: str | None, weekly: bool) -> None:
    """Print what a live run would do, reading only local state (warroom.db, x_state.json)."""
    start = _classify_start(today, classify_since)
    pending = _count("SELECT COUNT(*) FROM competitor_items WHERE date >= ? AND date <= ? AND category = 'pending'",
                     (start, today))
    if classify_since:
        print(f"[dry-run] Will classify {pending} pending items from {start} to {today} with Gemini; "
              "no collection and no brief")
        return

    handles = x_source._handles()
    state = json.loads(x_source.STATE.read_text(encoding="utf-8")) if x_source.STATE.exists() else {}
    users, since = state.get("users", {}), state.get("since", {})
    unresolved = [h for _, h in handles if h.lower() not in users]
    resumed = sum(1 for _, h in handles if users.get(h.lower()) in since)
    if os.environ.get("X_BEARER_TOKEN"):
        print(f"[dry-run] Will read {len(handles)} X accounts ({resumed} from their since_id, the rest from "
              f"the last {x_source.FIRST_READ_HOURS}h), looking up {len(unresolved)} new handles, "
              f"cap {os.environ.get('X_DAILY_POST_CAP', '300')} posts per UTC day")
    else:
        print("[dry-run] Will skip X: X_BEARER_TOKEN is not set")
    if os.environ.get("INGEST_API_TOKEN"):
        print(f"[dry-run] Will send the new posts to knowledge-api at {KNOWLEDGE_API}")
    else:
        print("[dry-run] Will not send posts to knowledge-api: INGEST_API_TOKEN is not set")
    print(f"[dry-run] Will classify {pending} pending items from {start} to {today}, plus the posts collected")
    print(f"[dry-run] Will write the labs daily brief for {today} if it has classified X posts")
    if weekly:
        end = date_cls.fromisoformat(today) - timedelta(days=1)
        from labs.daily import NOTHING

        days = _count("SELECT COUNT(*) FROM periodic_summaries WHERE period = 'labs_daily' "
                      "AND start_date >= ? AND end_date <= ? AND trim(content) != ?",
                      (str(end - timedelta(days=6)), str(end), NOTHING))
        print(f"[dry-run] Will write the labs weekly report for {end - timedelta(days=6)} ~ {end} "
              f"from {days} daily briefs")
    else:
        print("[dry-run] Will not write the weekly report (no --classify)")


def main():
    parser = argparse.ArgumentParser(
        description="前沿實驗室動態：收集官方 X 貼文、分類並寫每日快報（預設 dry-run，只列出會做的事）")
    parser.add_argument("--live", action="store_true",
                        help="真的讀 X、呼叫 Gemini 並寫入 knowledge-api（會產生費用）")
    parser.add_argument("--classify", action="store_true",
                        help="另外產出上週的實驗室週報（labs.sh 週一加上）；分類與每日快報每次都會跑")
    parser.add_argument("--date", type=str, default=None, help="指定日期（YYYY-MM-DD），預設今天 UTC")
    parser.add_argument("--classify-since", metavar="DATE",
                        help="只重新分類這天以來 category 為 pending 的項目，不收集也不寫簡報")
    args = parser.parse_args()

    today = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not args.live:
        dry_run(today, args.classify_since, args.classify)
        return

    init_db()
    if args.classify_since:
        run_classify(today, since=args.classify_since)
        return

    run_collect(today)
    run_classify(today)
    from labs.daily import generate_daily_brief
    generate_daily_brief(today)

    if args.classify:
        from labs.weekly import generate_weekly_from_daily
        console.print("\n[bold]Generating labs weekly report...[/]\n")
        generate_weekly_from_daily(today)


if __name__ == "__main__":
    main()
