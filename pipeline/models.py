"""
Shared data models for the pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    RSS = "rss"
    ARXIV = "arxiv"
    GITHUB = "github"
    LOBSTERS = "lobsters"
    GOOGLE_NEWS = "google_news"
    PRODUCTHUNT = "producthunt"


class NewsItem(BaseModel):
    """A single piece of news from any source."""
    title: str
    url: str
    source_type: SourceType
    source_name: str  # e.g. "r/LocalLLaMA", "OpenAI Blog", "HN"
    content: str = ""  # body text / summary / abstract
    score: int = 0  # upvotes, stars, etc.
    comments_count: int = 0
    published_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)

    def relevance_key(self) -> str:
        """For deduplication."""
        return self.url.rstrip("/")


class DailyDigest(BaseModel):
    """The final output for one day."""
    date: str  # YYYY-MM-DD
    title: str
    description: str  # 1-3 sentence summary
    news_items: list[DigestItem] = []
    strategic_insights: str = ""
    raw_item_count: int = 0


class DigestItem(BaseModel):
    """A summarized news item in the daily digest."""
    headline: str
    summary: str
    source: str
    url: str
    ref_id: str = ""  # e.g. "ref-1"
