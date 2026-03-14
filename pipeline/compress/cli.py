"""CLI entry point for compress module."""

from __future__ import annotations

import argparse
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console

from db import init_db
from compress.warroom import run_weekly, run_monthly, run_quarterly
from compress.industry import run_raw_weekly, run_raw_monthly, run_raw_quarterly

console = Console()


def run_auto(ref_date: datetime):
    """Auto-detect which summaries should be generated based on the date."""
    console.print(f"\n[bold]Auto mode — ref date: {ref_date.strftime('%Y-%m-%d')}[/]\n")

    ran_any = False

    if ref_date.weekday() == 0:
        console.print("[cyan]→ Monday detected, running weekly summaries[/]")
        run_weekly(ref_date)
        run_raw_weekly(ref_date)
        ran_any = True

    if ref_date.day == 1:
        console.print("[cyan]→ 1st of month detected, running monthly summaries[/]")
        run_monthly(ref_date)
        run_raw_monthly(ref_date)
        ran_any = True

    if ref_date.day == 1 and ref_date.month in (1, 4, 7, 10):
        console.print("[cyan]→ Quarter start detected, running quarterly summaries[/]")
        run_quarterly(ref_date)
        run_raw_quarterly(ref_date)
        ran_any = True

    if not ran_any:
        console.print(
            "[dim]No summaries to generate today. "
            "Weekly runs on Mon, monthly on 1st, quarterly on 1st of Jan/Apr/Jul/Oct.[/]"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Compress daily reports into periodic summaries"
    )
    parser.add_argument(
        "period",
        choices=["weekly", "monthly", "quarterly", "auto"],
        help="Which summary period to generate (runs both warroom + industry tracks)",
    )
    parser.add_argument(
        "--date", type=str, default=None, help="Reference date (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    load_dotenv()
    init_db()

    ref_date = (
        datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    )

    if args.period == "auto":
        run_auto(ref_date)
    elif args.period == "weekly":
        run_weekly(ref_date)
        run_raw_weekly(ref_date)
    elif args.period == "monthly":
        run_monthly(ref_date)
        run_raw_monthly(ref_date)
    elif args.period == "quarterly":
        run_quarterly(ref_date)
        run_raw_quarterly(ref_date)


if __name__ == "__main__":
    main()
