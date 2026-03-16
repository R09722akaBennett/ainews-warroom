"""Database connection and schema initialization."""

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
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_digests (
            date TEXT PRIMARY KEY,
            title TEXT,
            news_json TEXT,
            insights TEXT,
            raw_count INTEGER,
            tags TEXT,
            token_usage TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS news_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            topic TEXT,
            headline TEXT,
            summary TEXT,
            url TEXT,
            source TEXT,
            FOREIGN KEY (date) REFERENCES daily_digests(date)
        );

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

        CREATE INDEX IF NOT EXISTS idx_topics_topic ON news_topics(topic);
        CREATE INDEX IF NOT EXISTS idx_topics_date ON news_topics(date);
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

        CREATE TABLE IF NOT EXISTS legacy_issues (
            date TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            companies TEXT,
            models TEXT,
            topics TEXT,
            people TEXT,
            content TEXT
        );
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

    # Migrations: add columns if missing (for existing databases)
    for table, column, col_type in [
        ("daily_digests", "token_usage", "TEXT"),
        ("periodic_summaries", "token_usage", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # column already exists

    conn.commit()
    conn.close()
