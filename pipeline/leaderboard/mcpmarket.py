"""Scrape mcpmarket.com leaderboards — MCP Servers + Claude Skills."""

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Pages to scrape: key → (path, href_prefix for URL extraction)
PAGES = {
    "servers": ("/leaderboards", "/server/"),
    "skills": ("/tools/skills/leaderboard", "/tools/skills/"),
}


def _decode_unicode(s: str) -> str:
    """Decode \\uXXXX escape sequences in a string."""
    return re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda m: chr(int(m.group(1), 16)),
        s,
    )


def _parse_items(html: str, href_prefix: str, limit: int = 50) -> list[dict]:
    """Parse leaderboard from Next.js RSC flight payload.

    mcpmarket.com is a Next.js app with data in RSC flight chunks:
    - Names: font-semibold...children:"NAME"
    - Categories: uppercase tracking-wider...children:"CATEGORY"
    - Descriptions: line-clamp-2 text-sm...children:"DESC"
    - Stars: ],"{count}" (large comma-separated numbers after SVG paths)
    - URLs: href:"/server/slug" or href:"/tools/skills/slug" in RSC data
    """
    # Decode all RSC flight chunks
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html)
    all_rsc = "".join(
        c.replace('\\"', '"').replace("\\\\", "\\") for c in chunks
    )

    # Extract parallel arrays from RSC data
    names = re.findall(
        r'font-semibold text-foreground transition-colors '
        r'group-hover:text-foreground/80","children":"([^"]+)"',
        all_rsc,
    )
    categories = re.findall(
        r'uppercase tracking-wider text-muted-foreground","children":"([^"]+)"',
        all_rsc,
    )
    descriptions = re.findall(
        r'line-clamp-2 text-sm leading-relaxed text-muted-foreground","children":"([^"]+)"',
        all_rsc,
    )
    star_strs = re.findall(r'\],"([\d,]{3,})"', all_rsc)

    # Extract URLs from RSC href patterns (e.g. "/server/slug" or "/tools/skills/slug")
    href_pattern = re.escape(href_prefix)
    all_hrefs = re.findall(rf'"href":"({href_pattern}[^"]+)"', all_rsc)
    # Filter out navigation links (leaderboard, categories pages)
    item_hrefs = [
        h for h in all_hrefs
        if not h.endswith("/leaderboard")
        and not h.endswith("/categories")
        and h != href_prefix.rstrip("/")
    ]

    count = min(len(names), len(categories), len(descriptions), len(star_strs))
    items: list[dict] = []
    for i in range(min(count, limit)):
        name = _decode_unicode(names[i])
        stars = int(star_strs[i].replace(",", "")) if i < len(star_strs) else 0
        url = f"{BASE_URL}{item_hrefs[i]}" if i < len(item_hrefs) else ""
        items.append({
            "rank": i + 1,
            "name": name,
            "description": _decode_unicode(descriptions[i]) if i < len(descriptions) else "",
            "category": _decode_unicode(categories[i]) if i < len(categories) else "",
            "stars": stars,
            "url": url,
        })

    return items


def _fetch_page(path: str) -> str:
    """Fetch a page from mcpmarket.com."""
    resp = httpx.get(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


def fetch_mcpmarket() -> dict:
    """Fetch MCP Servers and Skills leaderboards."""
    result: dict = {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    for key, (path, href_prefix) in PAGES.items():
        console.print(f"  Fetching [cyan]{key}[/] leaderboard...", end=" ")
        try:
            html = _fetch_page(path)
            items = _parse_items(html, href_prefix, limit=50)
            result[key] = items
            console.print(f"[green]{len(items)} items[/]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            result[key] = []

    return result


def main():
    console.print("\n[bold]Fetching MCP Market Leaderboards...[/]\n")

    try:
        data = fetch_mcpmarket()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[yellow]Keeping existing mcpmarket.json if present.[/]")
        return

    total = len(data.get("servers", [])) + len(data.get("skills", []))
    if total == 0:
        console.print("[yellow]Warning: no items extracted. Keeping existing data.[/]")
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "mcpmarket.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(
        f"\n[bold green]Done! {len(data.get('servers', []))} servers + "
        f"{len(data.get('skills', []))} skills → src/data/mcpmarket.json[/]"
    )


if __name__ == "__main__":
    main()
