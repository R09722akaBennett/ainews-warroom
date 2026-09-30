"""
Database layer: SQLite storage for summaries, candidate raw items and lab items.
"""

from db.connection import get_conn, init_db
from db.summaries import (
    save_summary,
    get_latest_summary,
    get_latest_summaries,
    get_summaries_by_period,
    SummaryRecord,
    SummaryPeriod,
)
from db.raw_items import save_raw_items, get_raw_items, get_recent_urls
from db.competitor_items import save_competitor_items, get_competitor_items, get_competitor_urls

__all__ = [
    "get_conn",
    "init_db",
    "save_summary",
    "get_latest_summary",
    "get_latest_summaries",
    "get_summaries_by_period",
    "SummaryRecord",
    "SummaryPeriod",
    "save_raw_items",
    "get_raw_items",
    "get_recent_urls",
]
