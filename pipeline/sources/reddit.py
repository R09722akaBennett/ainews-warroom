"""
Reddit source — fetches top daily posts from AI-related subreddits.
Uses PRAW (Python Reddit API Wrapper). Requires Reddit API credentials.

Env vars needed:
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USER_AGENT  (optional, defaults to "ainews-pipeline/0.1")
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import praw

from models import NewsItem, SourceType
from config import REDDIT_SUBREDDITS, REDDIT_TOP_N_PER_SUB, REDDIT_TIME_FILTER


def fetch_reddit() -> list[NewsItem]:
    """Fetch top daily posts from AI subreddits."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "ainews-pipeline/0.1")

    if not client_id or not client_secret:
        print("[Reddit] Skipping — REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set")
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    items: list[NewsItem] = []

    for sub_name in REDDIT_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.top(time_filter=REDDIT_TIME_FILTER, limit=REDDIT_TOP_N_PER_SUB):
                items.append(NewsItem(
                    title=post.title,
                    url=f"https://reddit.com{post.permalink}" if not post.url.startswith("http") else post.url,
                    source_type=SourceType.REDDIT,
                    source_name=f"r/{sub_name}",
                    content=post.selftext[:2000] if post.selftext else "",
                    score=post.score,
                    comments_count=post.num_comments,
                    published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                    metadata={
                        "reddit_id": post.id,
                        "subreddit": sub_name,
                        "flair": post.link_flair_text or "",
                    },
                ))
        except Exception as e:
            print(f"[Reddit] Error fetching r/{sub_name}: {e}")

    items.sort(key=lambda x: x.score, reverse=True)
    return items
