"""Scrape arena.ai leaderboard and write to src/data/leaderboard.json.

Usage:
    cd pipeline
    uv run python -m leaderboard
"""

from leaderboard.scraper import main

main()
