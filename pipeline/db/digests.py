"""Daily digest CRUD operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from db.connection import get_conn


@dataclass
class DigestRecord:
    date: str
    title: str
    news_json: str
    insights: str
    raw_count: int
    tags: str | None = None
    token_usage: str | None = None
    created_at: str = ""


def save_digest(
    date: str,
    title: str,
    news_items: list[dict],
    insights: str,
    raw_count: int,
    topics: list[dict] | None = None,
    tags: dict | None = None,
    token_usage: dict | None = None,
):
    """Save a daily digest and its extracted topics."""
    conn = get_conn()
    tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
    token_json = json.dumps(token_usage) if token_usage else None
    conn.execute(
        "INSERT OR REPLACE INTO daily_digests (date, title, news_json, insights, raw_count, tags, token_usage) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (date, title, json.dumps(news_items, ensure_ascii=False), insights, raw_count, tags_json, token_json),
    )

    if topics:
        conn.execute("DELETE FROM news_topics WHERE date = ?", (date,))
        conn.executemany(
            "INSERT INTO news_topics (date, topic, headline, summary, url, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (date, t["topic"], t["headline"], t["summary"], t.get("url", ""), t.get("source", ""))
                for t in topics
            ],
        )

    conn.commit()
    conn.close()


def get_recent_digests(days: int = 3) -> list[DigestRecord]:
    """Get recent daily digests (default: last 3 days)."""
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT * FROM daily_digests WHERE date >= ? ORDER BY date DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [DigestRecord(**dict(row)) for row in rows]


def get_digest_by_date(date: str) -> DigestRecord | None:
    """Get a specific daily digest."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM daily_digests WHERE date = ?", (date,)
    ).fetchone()
    conn.close()
    return DigestRecord(**dict(row)) if row else None


def load_daily_digests(start: str, end: str) -> list[dict]:
    """Load daily digests in a date range (for compression)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, title, insights, raw_count FROM daily_digests "
        "WHERE date >= ? AND date <= ? ORDER BY date",
        (start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_related_history(
    keywords: list[str], days: int = 30, limit: int = 10
) -> list[dict]:
    """Search past digests for topics related to given keywords."""
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    results = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        rows = conn.execute(
            """
            SELECT date, topic, headline, summary, url, source
            FROM news_topics
            WHERE (topic LIKE ? OR headline LIKE ? OR summary LIKE ?)
              AND date >= ?
            ORDER BY date DESC LIMIT ?
            """,
            (pattern, pattern, pattern, cutoff, limit),
        ).fetchall()
        results.extend(dict(row) for row in rows)

    # Deduplicate by headline
    seen: set[str] = set()
    unique = []
    for r in results:
        if r["headline"] not in seen:
            seen.add(r["headline"])
            unique.append(r)

    unique.sort(key=lambda x: x["date"], reverse=True)
    return unique[:limit]
