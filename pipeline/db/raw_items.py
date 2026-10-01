"""Store the candidate items of each day (table raw_daily_items) for cross-day dedup."""

from __future__ import annotations

from db.connection import get_conn


def save_raw_items(date: str, items: list[dict]):
    """Replace the day's stored items with title, url, source and score of items."""
    conn = get_conn()
    conn.execute("DELETE FROM raw_daily_items WHERE date = ?", (date,))
    conn.executemany(
        "INSERT INTO raw_daily_items (date, title, url, source, score) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (date, it["title"], it.get("url", ""), it.get("source", ""), it.get("score", 0))
            for it in items
        ],
    )
    conn.commit()
    conn.close()


def get_recent_urls(date: str, days: int = 7) -> set[str]:
    """Return the URLs stored in the days before date, excluding date itself."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT url FROM raw_daily_items "
        "WHERE date < ? AND date >= date(?, '-' || ? || ' days') AND url != ''",
        (date, date, days),
    ).fetchall()
    conn.close()
    return {row["url"].rstrip("/") for row in rows}
