"""Shared data models for the pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    HACKERNEWS = "hackernews"
    RSS = "rss"
    LOBSTERS = "lobsters"
    GOOGLE_NEWS = "google_news"


class NewsItem(BaseModel):
    """A single piece of news from any source."""
    title: str
    url: str
    source_type: SourceType
    source_name: str  # e.g. "Hacker News", "OpenAI Blog"
    content: str = ""  # body text / summary / abstract
    score: int = 0  # upvotes, stars, etc.
    comments_count: int = 0
    published_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
