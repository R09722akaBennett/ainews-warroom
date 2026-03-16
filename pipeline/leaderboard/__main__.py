"""Scrape arena.ai leaderboard + alphaxiv trending papers.

Usage:
    cd pipeline
    uv run python -m leaderboard
"""

from leaderboard.scraper import main as leaderboard_main
from leaderboard.alphaxiv import main as papers_main

leaderboard_main()
papers_main()

