"""
ArXiv source — fetches latest AI/ML papers.
Uses the arxiv Python package (wraps the ArXiv API).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import arxiv

from models import NewsItem, SourceType
from config import ARXIV_CATEGORIES, ARXIV_MAX_RESULTS


def fetch_arxiv(hours: int = 48) -> list[NewsItem]:
    """
    Fetch recent papers from ArXiv AI categories.
    Uses 48h window because ArXiv updates aren't real-time.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen_ids: set[str] = set()
    items: list[NewsItem] = []

    for category in ARXIV_CATEGORIES:
        try:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=ARXIV_MAX_RESULTS,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            client = arxiv.Client()
            for paper in client.results(search):
                # Deduplicate across categories
                if paper.entry_id in seen_ids:
                    continue
                seen_ids.add(paper.entry_id)

                pub_date = paper.published.replace(tzinfo=timezone.utc)
                if pub_date < cutoff:
                    continue

                # Get primary category
                primary_cat = paper.primary_category or category

                items.append(NewsItem(
                    title=paper.title.replace("\n", " "),
                    url=paper.entry_id,
                    source_type=SourceType.ARXIV,
                    source_name=f"ArXiv {primary_cat}",
                    content=paper.summary.replace("\n", " ")[:2000],
                    published_at=pub_date,
                    metadata={
                        "arxiv_id": paper.entry_id,
                        "categories": list(paper.categories) if paper.categories else [primary_cat],
                        "authors": [a.name for a in paper.authors[:5]],
                        "pdf_url": paper.pdf_url,
                    },
                ))

        except Exception as e:
            print(f"[ArXiv] Error fetching {category}: {e}")

    return items
