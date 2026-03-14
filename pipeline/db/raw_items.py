"""Raw daily items CRUD operations."""

from __future__ import annotations

from db.connection import get_conn


def save_raw_items(date: str, items: list[dict]):
    """Save condensed raw items (title, url, source, score) for a given day."""
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


def get_raw_items(start: str, end: str) -> list[dict]:
    """Get raw items in a date range, ordered by date then score."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, title, url, source, score FROM raw_daily_items "
        "WHERE date >= ? AND date <= ? ORDER BY date, score DESC",
        (start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
