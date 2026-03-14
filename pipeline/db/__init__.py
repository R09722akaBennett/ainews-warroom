"""
Database layer — SQLite storage for digests, summaries, raw items, and legacy data.
"""

from db.connection import get_conn, init_db
from db.digests import (
    save_digest,
    get_recent_digests,
    get_digest_by_date,
    search_related_history,
    DigestRecord,
)
from db.summaries import (
    save_summary,
    get_latest_summary,
    get_latest_summaries,
    get_summaries_by_period,
    SummaryRecord,
    SummaryPeriod,
)
from db.raw_items import save_raw_items, get_raw_items

__all__ = [
    "get_conn",
    "init_db",
    "save_digest",
    "get_recent_digests",
    "get_digest_by_date",
    "search_related_history",
    "DigestRecord",
    "save_summary",
    "get_latest_summary",
    "get_latest_summaries",
    "get_summaries_by_period",
    "SummaryRecord",
    "SummaryPeriod",
    "save_raw_items",
    "get_raw_items",
]
