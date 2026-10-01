"""Scrape arena.ai leaderboard, alphaxiv trending papers and MCP Market.

Usage:
    cd pipeline
    uv run python -m leaderboard

Each scraper keeps the previous JSON when it fails or extracts nothing. The
exit code is non-zero if any of them did, so cron's alert wrapper notices;
when these failures exited 0 the data froze for months unnoticed.
"""

import sys

from leaderboard.alphaxiv import main as papers_main
from leaderboard.mcpmarket import main as mcpmarket_main
from leaderboard.scraper import main as leaderboard_main

results = {
    "leaderboard": leaderboard_main(),
    "alphaxiv": papers_main(),
    "mcpmarket": mcpmarket_main(),
}
failed = [name for name, ok in results.items() if not ok]
if failed:
    print(f"leaderboard: stale output kept for {', '.join(failed)}", file=sys.stderr)
    sys.exit(1)
