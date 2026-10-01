"""Store the labs' items (table competitor_items)."""

from __future__ import annotations

from db.connection import get_conn


def save_competitor_items(date: str, company: str, items: list[dict]):
    """Add items for this date and company, skipping URLs already stored for them.

    Rows are never replaced: X reads only posts newer than the last read, so
    replacing the day's rows on a second run would drop the earlier posts.
    """
    conn = get_conn()
    have = {r[0] for r in conn.execute(
        "SELECT url FROM competitor_items WHERE date = ? AND company = ?", (date, company))}
    items = [it for it in items if it.get("url", "") not in have]
    conn.executemany(
        "INSERT INTO competitor_items "
        "(date, company, title, url, source, published_at, category, ai_related, summary, content) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                date,
                company,
                it["title"],
                it.get("url", ""),
                it.get("source", ""),
                it.get("published_at"),
                # Unclassified items must be "pending": run_classify picks only those, and the
                # September 2026 X backfill, saved as "other", was never classified (494 of 509).
                it.get("category", "pending"),
                1 if it.get("ai_related", True) else 0,
                it.get("summary", ""),
                it.get("content", ""),
            )
            for it in items
        ],
    )
    conn.commit()
    conn.close()


def get_competitor_urls(date: str, days: int = 7) -> set[str]:
    """Return the item URLs stored in the days before date, for cross-day dedup."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT url FROM competitor_items "
        "WHERE date < ? AND date >= date(?, '-' || ? || ' days') AND url != ''",
        (date, date, days),
    ).fetchall()
    conn.close()
    return {row["url"].rstrip("/") for row in rows}
