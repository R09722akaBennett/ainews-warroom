"""Backfill old IDP weekly recaps by URL pattern.

Usage:
    uv run python -m idp.backfill --from 167 --to 186
"""

from __future__ import annotations

import argparse
import re
import time

import httpx
from dotenv import load_dotenv
from rich.console import Console

from db import init_db
from db.idp_items import upsert_idp_item
from idp.scraper import _strip_html, HEADERS, TIMEOUT
from idp.translator import translate_item
from db.idp_items import save_translation
from db.connection import get_conn
import json

console = Console()

URL_TMPL = "https://www.intelligentdocumentprocessing.com/idp-news-weekly-recap-{n}/"


def fetch_recap(n: int) -> dict | None:
    url = URL_TMPL.format(n=n)
    try:
        r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return None
        html_text = r.text
    except Exception as e:
        console.print(f"  [red]#{n} fetch error: {e}[/]")
        return None

    m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html_text)
    published_at = m.group(1)[:10] if m else None

    m = re.search(r"<article[^>]*>(.*?)</article>", html_text, re.S)
    body = m.group(1) if m else html_text
    raw_text = _strip_html(body)
    if len(raw_text) < 300:
        return None

    return {
        "guid": url,
        "url": url,
        "title": f"Intelligent Document Processing News: Weekly Recap #{n}",
        "kind": "weekly_recap",
        "published_at": published_at,
        "vendors": [],
        "categories": ["Weekly Recap"],
        "raw_html": body,
        "raw_text": raw_text,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_n", type=int, required=True)
    p.add_argument("--to", dest="to_n", type=int, required=True)
    p.add_argument("--no-translate", action="store_true")
    args = p.parse_args()

    load_dotenv()
    init_db()

    fetched: list[dict] = []
    new_ids: list[tuple[int, dict]] = []
    for n in range(args.to_n, args.from_n - 1, -1):
        console.print(f"  fetching #{n}...", end=" ")
        item = fetch_recap(n)
        if not item:
            console.print("[yellow]skip[/]")
            continue
        rid, is_new = upsert_idp_item(item)
        console.print(f"[green]{'+ new' if is_new else 'updated'}[/] ({item['published_at']})")
        if is_new:
            item["id"] = rid
            new_ids.append((rid, item))
        time.sleep(0.5)

    if args.no_translate or not new_ids:
        console.print(f"\n[bold]Fetched {len(new_ids)} new items[/]")
        return

    console.print(f"\n[bold]Translating {len(new_ids)} items...[/]")
    total = {"input": 0, "output": 0, "total": 0}
    for rid, item in new_ids:
        console.print(f"  #{item['title'][-6:].rstrip('/')}...", end=" ")
        parsed, usage = translate_item(item)
        if not parsed:
            console.print("[red]skip[/]")
            continue
        save_translation(rid, parsed.get("summary_md", ""), parsed.get("title"), usage)
        vendors_llm = parsed.get("vendors") or []
        if vendors_llm:
            conn = get_conn()
            conn.execute(
                "UPDATE idp_items SET vendors=? WHERE id=?",
                (json.dumps(vendors_llm, ensure_ascii=False), rid),
            )
            conn.commit()
            conn.close()
        if usage:
            for k in total:
                total[k] += usage.get(k, 0)
        console.print("[green]ok[/]")

    console.print(f"\n[bold]Tokens: in={total['input']:,} out={total['output']:,}[/]")


if __name__ == "__main__":
    main()
