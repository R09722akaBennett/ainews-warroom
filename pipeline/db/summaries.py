"""Store and load periodic summaries (daily briefs, weekly reports, token records)."""

from __future__ import annotations

import json

from db.connection import get_conn


def save_summary(
    period: str, start_date: str, end_date: str, title: str, content: str,
    tags: dict | None = None,
    token_usage: dict | None = None,
):
    """Save a periodic summary, replacing the one with the same period and dates."""
    conn = get_conn()
    tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
    token_json = json.dumps(token_usage) if token_usage else None
    conn.execute(
        """
        INSERT OR REPLACE INTO periodic_summaries
        (period, start_date, end_date, title, content, tags, token_usage)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (period, start_date, end_date, title, content, tags_json, token_json),
    )
    conn.commit()
    conn.close()


def load_summaries(period: str, start: str, end: str) -> list[dict]:
    """Return the summaries of period that lie within start..end, oldest first."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT start_date, end_date, title, content FROM periodic_summaries "
        "WHERE period = ? AND start_date >= ? AND end_date <= ? ORDER BY start_date",
        (period, start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
