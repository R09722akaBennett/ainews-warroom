"""Date range helpers for periodic compression."""

from __future__ import annotations

from datetime import datetime, timedelta


def week_range(ref_date: datetime) -> tuple[str, str]:
    """Get Monday-Sunday range for the week containing ref_date."""
    weekday = ref_date.weekday()
    monday = ref_date - timedelta(days=weekday)
    sunday = monday + timedelta(days=6)
    return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def last_week_range(ref_date: datetime) -> tuple[str, str]:
    return week_range(ref_date - timedelta(days=7))


def last_month_range(ref_date: datetime) -> tuple[str, str]:
    first_of_this_month = ref_date.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev.strftime("%Y-%m-%d"), last_of_prev.strftime("%Y-%m-%d")


def last_quarter_range(ref_date: datetime) -> tuple[str, str]:
    month = ref_date.month
    year = ref_date.year
    q_start_month = ((month - 1) // 3) * 3 + 1
    if q_start_month == 1:
        prev_q_start = datetime(year - 1, 10, 1)
        prev_q_end = datetime(year - 1, 12, 31)
    else:
        prev_q_start = datetime(year, q_start_month - 3, 1)
        prev_q_end = datetime(year, q_start_month, 1) - timedelta(days=1)
    return prev_q_start.strftime("%Y-%m-%d"), prev_q_end.strftime("%Y-%m-%d")
