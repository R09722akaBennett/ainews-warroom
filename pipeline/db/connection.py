"""Open warroom.db and create its schema."""

from __future__ import annotations

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "warroom.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the tables the pipeline uses and add missing columns; safe to run on every start.

    daily_digests, news_topics and legacy_issues are no longer created;
    databases that already have them keep them, since nothing here drops a
    table.
    """
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS periodic_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            title TEXT,
            content TEXT,
            tags TEXT,
            token_usage TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(period, start_date, end_date)
        );

        CREATE INDEX IF NOT EXISTS idx_summaries_period ON periodic_summaries(period);
        CREATE INDEX IF NOT EXISTS idx_summaries_dates ON periodic_summaries(start_date, end_date);

        CREATE TABLE IF NOT EXISTS raw_daily_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            source TEXT,
            score REAL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_raw_date ON raw_daily_items(date);
        CREATE INDEX IF NOT EXISTS idx_raw_url ON raw_daily_items(url);
    """)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS competitor_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            source TEXT,
            published_at TEXT,
            category TEXT DEFAULT 'other',
            ai_related INTEGER DEFAULT 1,
            summary TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_competitor_date ON competitor_items(date);
        CREATE INDEX IF NOT EXISTS idx_competitor_company ON competitor_items(company);
        CREATE INDEX IF NOT EXISTS idx_competitor_url ON competitor_items(url);
    """)

    for table, column, col_type in [
        ("periodic_summaries", "token_usage", "TEXT"),
        # Item text was only passed to the classifier in memory and never stored,
        # so later classification saw titles alone.
        ("competitor_items", "content", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()
    conn.close()
