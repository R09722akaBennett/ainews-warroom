"""Scrape alphaxiv.org trending papers — Hot + Likes top 10."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")

BASE_URL = "https://www.alphaxiv.org/"


def _scrape_papers(sort: str, limit: int = 10) -> list[dict]:
    """Scrape top papers from alphaxiv sorted by Hot or Likes."""
    resp = httpx.get(
        f"{BASE_URL}?sort={sort}",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        },
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    papers: list[dict] = []
    seen: set[str] = set()

    for link in soup.select('a[href^="/abs/"]'):
        arxiv_id = link.get("href", "").replace("/abs/", "").strip()
        title = link.get_text(strip=True)
        if not arxiv_id or arxiv_id in seen or not title or len(title) < 10:
            continue
        seen.add(arxiv_id)

        # Walk up to card container
        card = link
        for _ in range(8):
            if card.parent and "rounded-xl" in " ".join(card.parent.get("class", [])):
                card = card.parent
                break
            card = card.parent or card

        # Date
        card_text = card.get_text(" | ", strip=True)
        date_match = re.search(r"(\d{1,2}\s+\w{3}\s+\d{4})", card_text)
        date_str = date_match.group(1) if date_match else ""

        # Authors from individual name divs
        authors: list[str] = []
        for div in card.select("div.flex.items-center"):
            classes = " ".join(div.get("class", []))
            if "gap-1.5" in classes and "font" in classes:
                name = div.get_text(strip=True)
                if name and re.match(r"^[A-Z]", name) and len(name) < 40:
                    authors.append(name)

        # Numbers: votes and visits
        all_nums = [
            n.strip()
            for n in card.find_all(string=re.compile(r"^[\d,]+$"))
            if n.strip()
        ]
        votes = int(all_nums[0].replace(",", "")) if all_nums else 0
        visits = int(all_nums[-1].replace(",", "")) if len(all_nums) > 1 else 0

        # GitHub stars
        gh_stars = 0
        gh_link = card.select_one('a[href*="github.com"]')
        if gh_link:
            star_text = gh_link.get_text(strip=True)
            star_match = re.search(r"([\d,]+)", star_text)
            if star_match:
                gh_stars = int(star_match.group(1).replace(",", ""))

        # Summary from alphaxiv's AI-generated description
        summary_el = card.select_one("p.line-clamp-4")
        summary = summary_el.get_text(strip=True) if summary_el else ""

        # Categories (both main + sub)
        categories = []
        for a in card.select('a'):
            href = a.get("href", "")
            if "categories=" in href or "subcategories=" in href:
                tag = a.get_text(strip=True).lstrip("#")
                if tag and tag not in categories:
                    categories.append(tag)

        papers.append({
            "rank": len(papers) + 1,
            "arxivId": arxiv_id,
            "title": title,
            "summary": summary,
            "date": date_str,
            "authors": authors[:5],
            "votes": votes,
            "visits": visits,
            "ghStars": gh_stars,
            "categories": categories[:3],
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "alphaxivUrl": f"https://www.alphaxiv.org/abs/{arxiv_id}",
        })

        if len(papers) >= limit:
            break

    return papers


def fetch_trending_papers() -> dict:
    """Fetch Hot and Likes papers from alphaxiv."""
    console.print("  Fetching [cyan]Hot[/] papers...", end=" ")
    hot = _scrape_papers("Hot", limit=20)
    console.print(f"[green]{len(hot)} papers[/]")

    console.print("  Fetching [cyan]Likes[/] papers...", end=" ")
    likes = _scrape_papers("Likes", limit=20)
    console.print(f"[green]{len(likes)} papers[/]")

    return {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hot": hot,
        "likes": likes,
    }


def main():
    console.print("\n[bold]Fetching alphaxiv Trending Papers...[/]\n")

    try:
        data = fetch_trending_papers()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[yellow]Keeping existing papers.json if present.[/]")
        return

    total = len(data["hot"]) + len(data["likes"])
    if total == 0:
        console.print("[yellow]Warning: no papers extracted.[/]")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "papers.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold green]Done! {len(data['hot'])} hot + {len(data['likes'])} liked → src/data/papers.json[/]")


if __name__ == "__main__":
    main()
