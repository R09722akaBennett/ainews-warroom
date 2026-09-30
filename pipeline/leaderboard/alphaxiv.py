"""Fetch alphaxiv.org trending papers (Hot + Likes, top 20 each).

Uses the JSON feed the alphaxiv web app itself calls. The HTML pages sit
behind a Cloudflare challenge for datacenter IPs (bennett-hub gets 403 since
at least 2026-10-01), while api.alphaxiv.org does not.

Each run is a snapshot that replaces papers.json; nothing accumulates across
days, so a paper staying on the list for several days is expected and is not
a duplicate. Within one ranking a paper appears once.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import httpx
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")

FEED_URL = "https://api.alphaxiv.org/papers/v3/feed"
HEADERS = {"User-Agent": "Mozilla/5.0"}
# papers.json key → API sort value. The site labels "Hot" as "Trending".
SORTS = {"hot": "Hot", "likes": "Likes"}
# The web app defaults to a 7-day window; the API rejects a missing interval.
INTERVAL = "7 Days"


def _fetch(sort: str, limit: int) -> list[dict]:
    resp = httpx.get(FEED_URL, headers=HEADERS, timeout=30, params={
        "pageNum": "0", "pageSize": str(limit), "sort": sort,
        "interval": INTERVAL, "topics": "[]", "linkBlogs": "true",
    })
    resp.raise_for_status()
    return resp.json().get("papers") or []


def _to_item(rank: int, p: dict) -> dict:
    aid = p.get("universal_paper_id") or ""
    metrics = p.get("metrics") or {}
    summary = p.get("paper_summary") or {}
    published = (p.get("publication_date") or p.get("first_publication_date") or "")[:10]
    try:
        date = datetime.strptime(published, "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        date = ""
    topics = [t for t in (p.get("topics") or []) if t != "Computer Science"]
    return {
        "rank": rank,
        "arxivId": aid,
        "title": (p.get("title") or "").strip(),
        "summary": (summary.get("summary") if isinstance(summary, dict) else "") or (p.get("abstract") or "")[:400],
        "date": date,
        "authors": (p.get("authors") or [])[:5],
        "votes": int(metrics.get("public_total_votes") or metrics.get("total_votes") or 0),
        "visits": int((metrics.get("visits_count") or {}).get("all") or 0),
        "ghStars": int(p.get("github_stars") or 0),
        "categories": topics[:3],
        "url": f"https://arxiv.org/abs/{aid}",
        "alphaxivUrl": f"https://www.alphaxiv.org/abs/{aid}",
    }


def _scrape_papers(sort: str, limit: int = 20) -> list[dict]:
    items, seen = [], set()
    for p in _fetch(sort, limit):
        aid = p.get("universal_paper_id")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        items.append(_to_item(len(items) + 1, p))
    return items


def fetch_trending_papers() -> dict:
    """Fetch Hot and Likes rankings from alphaxiv."""
    result = {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for key, sort in SORTS.items():
        console.print(f"  Fetching [cyan]{sort}[/] papers...", end=" ")
        result[key] = _scrape_papers(sort, limit=20)
        console.print(f"[green]{len(result[key])} papers[/]")
    return result


def main() -> bool:
    """Refresh the JSON file; return False when it was left untouched."""
    console.print("\n[bold]Fetching alphaxiv Trending Papers...[/]\n")
    try:
        data = fetch_trending_papers()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[yellow]Keeping existing papers.json if present.[/]")
        return False
    if not data["hot"] or not data["likes"]:
        console.print("[yellow]Warning: a ranking came back empty. Keeping existing data.[/]")
        return False
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "papers.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"\n[bold green]Done! {len(data['hot'])} hot + {len(data['likes'])} liked → src/data/papers.json[/]")
    return True


if __name__ == "__main__":
    main()
