"""Periodic summary CRUD operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from db.connection import get_conn


class SummaryPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class SummaryRecord:
    period: str
    start_date: str
    end_date: str
    title: str
    content: str
    tags: str | None = None
    created_at: str = ""


def save_summary(
    period: str, start_date: str, end_date: str, title: str, content: str,
    tags: dict | None = None,
    token_usage: dict | None = None,
):
    """Save a periodic summary."""
    import json
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


def get_latest_summary(period: str) -> SummaryRecord | None:
    """Get the most recent summary for a given period type."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT period, start_date, end_date, title, content, tags, created_at
        FROM periodic_summaries
        WHERE period = ?
        ORDER BY end_date DESC LIMIT 1
        """,
        (period,),
    ).fetchone()
    conn.close()
    return SummaryRecord(**dict(row)) if row else None


def get_latest_summaries() -> dict[str, SummaryRecord | None]:
    """Get the latest summary for each period type."""
    return {
        "weekly": get_latest_summary(SummaryPeriod.WEEKLY),
        "monthly": get_latest_summary(SummaryPeriod.MONTHLY),
        "quarterly": get_latest_summary(SummaryPeriod.QUARTERLY),
    }


def get_summaries_by_period(period: str, limit: int = 5) -> list[SummaryRecord]:
    """Get recent summaries for a given period type."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT period, start_date, end_date, title, content, tags, created_at
        FROM periodic_summaries
        WHERE period = ?
        ORDER BY end_date DESC LIMIT ?
        """,
        (period, limit),
    ).fetchall()
    conn.close()
    return [SummaryRecord(**dict(row)) for row in rows]


def load_summaries(period: str, start: str, end: str) -> list[dict]:
    """Load summaries in a date range (for compression)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT start_date, end_date, title, content FROM periodic_summaries "
        "WHERE period = ? AND start_date >= ? AND end_date <= ? ORDER BY start_date",
        (period, start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
