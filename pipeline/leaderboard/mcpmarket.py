"""Scrape mcpmarket.com leaderboards — MCP Servers + Agent Skills.

Reads the schema.org ItemList that both leaderboard pages embed as JSON-LD.
The earlier version parsed Next.js RSC flight chunks by class name and broke
silently when the markup changed (mcpmarket.json froze for months). The
JSON-LD carries name, description, url and the star count but no category,
so `category` is left empty and the site hides its filter pills.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import httpx
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")

BASE_URL = "https://mcpmarket.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}

# key → (path, url prefix that identifies an item link)
PAGES = {
    "servers": ("/leaderboards", f"{BASE_URL}/server/"),
    "skills": ("/tools/skills/leaderboard", f"{BASE_URL}/tools/skills/"),
}


def _fetch_page(path: str) -> str:
    resp = httpx.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _parse_items(html: str, url_prefix: str, limit: int = 50) -> list[dict]:
    items: list[dict] = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "ItemList":
            continue
        for el in data.get("itemListElement", []):
            item = el.get("item")
            if not isinstance(item, dict) or not str(item.get("url", "")).startswith(url_prefix):
                continue
            stat = item.get("interactionStatistic") or {}
            items.append({
                "rank": len(items) + 1,
                "name": (item.get("name") or "").strip(),
                "description": (item.get("description") or "").strip(),
                "category": "",
                "stars": int(stat.get("userInteractionCount") or 0),
                "url": item["url"],
            })
            if len(items) >= limit:
                return items
    return items


def fetch_mcpmarket() -> dict:
    """Fetch MCP Servers and Agent Skills leaderboards."""
    result: dict = {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for key, (path, prefix) in PAGES.items():
        console.print(f"  Fetching [cyan]{key}[/] leaderboard...", end=" ")
        try:
            result[key] = _parse_items(_fetch_page(path), prefix, limit=50)
            console.print(f"[green]{len(result[key])} items[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            result[key] = []
    return result


def main() -> bool:
    """Refresh the JSON file; return False when it was left untouched."""
    console.print("\n[bold]Fetching MCP Market Leaderboards...[/]\n")
    try:
        data = fetch_mcpmarket()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[yellow]Keeping existing mcpmarket.json if present.[/]")
        return False
    path = os.path.join(DATA_DIR, "mcpmarket.json")
    empty = [k for k in PAGES if not data.get(k)]
    if len(empty) == len(PAGES):
        console.print("[yellow]Warning: no items extracted. Keeping existing data.[/]")
        return False
    if empty:
        # Keep the previous list for a page that failed instead of blanking it.
        try:
            with open(path, encoding="utf-8") as f:
                previous = json.load(f)
        except (OSError, json.JSONDecodeError):
            previous = {}
        for k in empty:
            data[k] = previous.get(k, [])
        console.print(f"[yellow]Warning: kept previous {', '.join(empty)} list.[/]")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"\n[bold green]Done! {len(data['servers'])} servers + {len(data['skills'])} skills → src/data/mcpmarket.json[/]")
    return not empty


if __name__ == "__main__":
    main()
