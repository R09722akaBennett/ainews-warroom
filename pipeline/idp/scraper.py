"""IDP Community RSS scraper.

Source: https://www.intelligentdocumentprocessing.com/feed/

Each RSS item is classified into one of three kinds:
  - weekly_recap: title contains "Weekly Recap" / category contains "Weekly Recap"
  - opinion:     category contains "Opinions"
  - news:        everything else (e.g. category "News")

The site's RSS <category> tags include vendor names (Planet AI, ABBYY, Konfuzio,
Parashift, ...). We strip out generic / meta categories so the rest can be used
as a vendor filter on the website without an extra LLM pass.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx
from rich.console import Console

console = Console()

FEED_URL = "https://www.intelligentdocumentprocessing.com/feed/"
TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KDAN-AI-WarRoom/1.0; "
        "+https://github.com/r09722050akabennett/ainews-warroom)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
}

# Categories that are not vendors (lower-cased)
GENERIC_CATEGORIES = {
    "news",
    "opinions",
    "weekly recap",
    "intelligent document processing",
    "idp",
    "uncategorized",
    "general",
    "events",
    "interviews",
}

# Heuristic: if a category looks like a person name ("First Last"), drop it.
# Only used after the GENERIC_CATEGORIES filter.
_PERSON_RE = re.compile(r"^(?:Dr\.|Mr\.|Mrs\.|Ms\.)\s")


def _is_person(name: str) -> bool:
    if _PERSON_RE.match(name):
        return True
    # Two-token capitalised name with no acronym / digit / dot
    parts = name.split()
    if len(parts) == 2 and all(p[:1].isupper() and p[1:].islower() and p.isalpha() for p in parts):
        return True
    return False


def _strip_html(s: str) -> str:
    s = re.sub(r"<script[^>]*>.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style[^>]*>.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _classify_kind(title: str, categories: list[str]) -> str:
    cats_lower = {c.lower() for c in categories}
    if "weekly recap" in cats_lower or "weekly recap" in title.lower():
        return "weekly_recap"
    if "opinions" in cats_lower or "opinion" in cats_lower:
        return "opinion"
    return "news"


def _extract_vendors(categories: list[str]) -> list[str]:
    vendors = []
    seen = set()
    for c in categories:
        cl = c.strip()
        if not cl:
            continue
        if cl.lower() in GENERIC_CATEGORIES:
            continue
        if _is_person(cl):
            continue
        key = cl.lower()
        if key in seen:
            continue
        seen.add(key)
        vendors.append(cl)
    return vendors


def _parse_pubdate(s: str | None) -> str | None:
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date().isoformat()
    except Exception:
        return None


def fetch_feed_items() -> list[dict]:
    """Download the RSS feed and return parsed items."""
    console.print(f"  Fetching [cyan]{FEED_URL}[/]...", end=" ")
    resp = httpx.get(FEED_URL, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    console.print(f"[green]{len(resp.content)} bytes[/]")

    root = ET.fromstring(resp.content)
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    items: list[dict] = []
    for el in root.iter("item"):
        title = (el.findtext("title") or "").strip()
        link = (el.findtext("link") or "").strip()
        guid = (el.findtext("guid") or link or title).strip()
        pubdate = el.findtext("pubDate")
        desc = el.findtext("description") or ""
        encoded = el.find("content:encoded", ns)
        content_html = encoded.text if encoded is not None and encoded.text else desc

        categories = [c.text.strip() for c in el.findall("category") if c.text and c.text.strip()]
        kind = _classify_kind(title, categories)
        vendors = _extract_vendors(categories)
        published_at = _parse_pubdate(pubdate)
        raw_text = _strip_html(content_html)

        items.append({
            "guid": guid,
            "url": link,
            "title": title,
            "kind": kind,
            "published_at": published_at,
            "vendors": vendors,
            "categories": categories,
            "raw_html": content_html,
            "raw_text": raw_text,
        })

    return items
