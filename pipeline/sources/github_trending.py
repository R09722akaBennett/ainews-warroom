"""
GitHub Trending source — scrapes trending AI/ML repositories.
GitHub doesn't have an official trending API, so we scrape the page.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from models import NewsItem, SourceType
from config import GITHUB_TRENDING_LANGUAGES


def _scrape_trending(language: str = "") -> list[dict]:
    """Scrape GitHub trending page for a given language."""
    url = "https://github.com/trending"
    params = {"since": "daily", "spoken_language_code": "en"}
    if language:
        url = f"{url}/{language}"

    try:
        resp = httpx.get(url, params=params, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[GitHub] Error fetching trending/{language}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []

    for article in soup.select("article.Box-row"):
        # Repo name
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        repo_path = h2.get("href", "").strip("/")
        if not repo_path:
            continue

        # Description
        p = article.select_one("p")
        desc = p.get_text(strip=True) if p else ""

        # Stars today
        stars_today = 0
        spans = article.select("span.d-inline-block.float-sm-right")
        if spans:
            text = spans[0].get_text(strip=True).replace(",", "")
            stars_today = int("".join(c for c in text if c.isdigit()) or "0")

        # Total stars
        total_stars = 0
        star_links = article.select("a.Link--muted")
        for link in star_links:
            href = link.get("href", "")
            if "/stargazers" in href:
                text = link.get_text(strip=True).replace(",", "")
                total_stars = int("".join(c for c in text if c.isdigit()) or "0")
                break

        # Language
        lang_span = article.select_one("span[itemprop='programmingLanguage']")
        lang = lang_span.get_text(strip=True) if lang_span else ""

        repos.append({
            "repo": repo_path,
            "description": desc,
            "stars_today": stars_today,
            "total_stars": total_stars,
            "language": lang,
        })

    return repos


# AI/ML keywords to filter repos
_AI_KEYWORDS = {
    "llm", "gpt", "transformer", "diffusion", "neural", "ai", "ml",
    "machine-learning", "deep-learning", "nlp", "langchain", "llama",
    "openai", "anthropic", "embedding", "rag", "agent", "chat",
    "vision", "whisper", "stable-diffusion", "fine-tune", "lora",
    "inference", "model", "tokenizer", "huggingface", "benchmark",
}


def _is_ai_repo(repo: dict) -> bool:
    combined = f"{repo['repo']} {repo['description']}".lower()
    return any(kw in combined for kw in _AI_KEYWORDS)


def fetch_github_trending() -> list[NewsItem]:
    """Fetch today's trending AI/ML repositories from GitHub."""
    seen: set[str] = set()
    items: list[NewsItem] = []

    for lang in GITHUB_TRENDING_LANGUAGES:
        repos = _scrape_trending(lang)
        for repo in repos:
            if repo["repo"] in seen:
                continue
            seen.add(repo["repo"])

            if not _is_ai_repo(repo):
                continue

            items.append(NewsItem(
                title=repo["repo"],
                url=f"https://github.com/{repo['repo']}",
                source_type=SourceType.GITHUB,
                source_name="GitHub Trending",
                content=repo["description"],
                score=repo["stars_today"],
                published_at=datetime.now(timezone.utc),
                metadata={
                    "total_stars": repo["total_stars"],
                    "language": repo["language"],
                    "stars_today": repo["stars_today"],
                },
            ))

    items.sort(key=lambda x: x.score, reverse=True)
    return items
