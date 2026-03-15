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
    conn.commit()
    conn.close()
