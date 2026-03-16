"""Export site data — reads warroom.db and writes JSON files for Astro.

Usage:
    cd pipeline
    uv run python -m export.site
"""

from __future__ import annotations

import json
import os

from rich.console import Console

from db import init_db
from db.connection import get_conn

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")


def _guess_source(url: str) -> str:
    """Infer source name from URL when source field is empty."""
    if not url:
        return "Other"
    domain = url.split("/")[2] if url.startswith("http") and len(url.split("/")) > 2 else ""
    if "github.com" in domain:
        return "GitHub"
    if "arxiv.org" in domain:
        return "ArXiv"
    if "reddit.com" in domain:
        return "Reddit"
    if "news.ycombinator.com" in domain:
        return "Hacker News"
    return domain.replace("www.", "") if domain else "Other"


def _normalize_source(source: str) -> str:
    """Normalize source names for consistent grouping."""
    if source.startswith("Google News ("):
        return "Google News"
    if source.startswith("ArXiv"):
        return "ArXiv"
    return source


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (---...---) from markdown content."""
    if not text or not text.startswith("---"):
        return text or ""
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3:].lstrip("\n")


def export_reports():
    """Export daily war room reports with structured refs."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, title, news_json, insights, raw_count, tags, token_usage, created_at "
        "FROM daily_digests ORDER BY date DESC"
    ).fetchall()

    topic_rows = conn.execute(
        "SELECT date, headline, url, source FROM news_topics ORDER BY date, id"
    ).fetchall()

    raw_rows = conn.execute(
        "SELECT date, title, url, source, score FROM raw_daily_items ORDER BY date, score DESC"
    ).fetchall()
    conn.close()

    refs_by_date: dict[str, list[dict]] = {}
    for t in topic_rows:
        refs_by_date.setdefault(t["date"], []).append({
            "headline": t["headline"],
            "url": t["url"],
            "source": t["source"],
        })

    reports = []
    for r in rows:
        tags = json.loads(r["tags"]) if r["tags"] else {}
        token_usage = json.loads(r["token_usage"]) if r["token_usage"] else None
        # news_json stores items in prompt order — used for ref-N fallback
        news_items = json.loads(r["news_json"]) if r["news_json"] else []
        entry: dict = {
            "date": r["date"],
            "title": r["title"],
            "content": strip_frontmatter(r["insights"]),
            "rawCount": r["raw_count"],
            "createdAt": r["created_at"],
            "refs": refs_by_date.get(r["date"], []),
            "newsItems": [{"url": it.get("url", ""), "title": it.get("title", ""), "source": _normalize_source(it.get("source", ""))} for it in news_items],
            "tags": tags,
        }
        if token_usage:
            entry["tokenUsage"] = token_usage
        reports.append(entry)

    path = os.path.join(DATA_DIR, "reports.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    # Export raw items separately (sources.json) — keyed by date
    sources_list = []
    for item in raw_rows:
        source = _normalize_source(item["source"] or _guess_source(item["url"]))
        sources_list.append({
            "date": item["date"],
            "title": item["title"],
            "url": item["url"],
            "source": source,
            "score": item["score"] or 0,
        })

    path = os.path.join(DATA_DIR, "sources.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sources_list, f, ensure_ascii=False, indent=2)

    console.print(f"  [green]✓[/] reports.json: {len(reports)} reports")
    console.print(f"  [green]✓[/] sources.json: {len(sources_list)} raw items")
    return len(reports)


def export_summaries():
    """Export all periodic summaries."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT period, start_date, end_date, title, content, tags, token_usage, created_at "
        "FROM periodic_summaries ORDER BY period, start_date DESC"
    ).fetchall()
    conn.close()

    summaries = []
    for r in rows:
        tags = json.loads(r["tags"]) if r["tags"] else {}
        token_usage = json.loads(r["token_usage"]) if r["token_usage"] else None
        entry: dict = {
            "period": r["period"],
            "startDate": r["start_date"],
            "endDate": r["end_date"],
            "title": r["title"],
            "content": r["content"],
            "createdAt": r["created_at"],
            "tags": tags,
        }
        if token_usage:
            entry["tokenUsage"] = token_usage
        summaries.append(entry)

    path = os.path.join(DATA_DIR, "summaries.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    console.print(f"  [green]✓[/] summaries.json: {len(summaries)} summaries")
    return len(summaries)


def export_legacy():
    """Export legacy smol.ai issue metadata + content."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, title, description, companies, models, topics, people, content "
        "FROM legacy_issues ORDER BY date DESC"
    ).fetchall()
    conn.close()

    legacy = []
    content_count = 0
    for r in rows:
        has_content = bool(r["content"])
        if has_content:
            content_count += 1
        legacy.append({
            "date": r["date"],
            "title": r["title"],
            "description": r["description"],
            "companies": json.loads(r["companies"]) if r["companies"] else [],
            "models": json.loads(r["models"]) if r["models"] else [],
            "topics": json.loads(r["topics"]) if r["topics"] else [],
            "people": json.loads(r["people"]) if r["people"] else [],
            "hasContent": has_content,
        })

    # Metadata-only index (lightweight, used by archive listing)
    path = os.path.join(DATA_DIR, "legacy.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(legacy, f, ensure_ascii=False, indent=2)

    # Full content keyed by date (used by individual issue pages at build time)
    content_map = {}
    for r in rows:
        if r["content"]:
            content_map[r["date"]] = r["content"]

    path = os.path.join(DATA_DIR, "legacy-content.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content_map, f, ensure_ascii=False)

    console.print(f"  [green]✓[/] legacy.json: {len(legacy)} issues ({content_count} with content)")
    return len(legacy)


def main():
    init_db()
    os.makedirs(DATA_DIR, exist_ok=True)

    console.print("\n[bold]Exporting site data from warroom.db...[/]\n")

    r = export_reports()
    s = export_summaries()
    lg = export_legacy()

    console.print(
        f"\n[bold green]Done! {r} reports + {s} summaries + {lg} legacy issues → src/data/[/]"
    )


if __name__ == "__main__":
    main()
