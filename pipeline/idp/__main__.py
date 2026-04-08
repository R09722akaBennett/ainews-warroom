"""IDP Community pipeline — fetch RSS + translate weekly recaps & opinions.

Usage:
    cd pipeline
    uv run python -m idp                  # fetch + translate new items
    uv run python -m idp --no-translate   # fetch only (skip LLM)
    uv run python -m idp --retranslate    # re-translate all (overwrite)
"""

from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv
from rich.console import Console

from db import init_db
from db.connection import get_conn
from db.idp_items import upsert_idp_item, save_translation, get_untranslated
from idp.scraper import fetch_feed_items
from idp.translator import translate_item

console = Console()

TRANSLATE_KINDS = ("weekly_recap", "opinion")


def run_fetch() -> tuple[int, int]:
    console.print("\n[bold]IDP Community — Fetch RSS[/]\n")
    try:
        items = fetch_feed_items()
    except Exception as e:
        console.print(f"[red]RSS fetch failed: {e}[/]")
        return 0, 0

    new_count = 0
    for it in items:
        _, is_new = upsert_idp_item(it)
        if is_new:
            new_count += 1
            console.print(f"  [green]+[/] [{it['kind']}] {it['title']}")

    console.print(f"\n  Total: {len(items)} items, [green]{new_count} new[/]")
    return len(items), new_count


def run_translate(retranslate: bool = False):
    console.print("\n[bold]IDP Community — Translate (LLM)[/]\n")

    if retranslate:
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, guid, url, title, kind, published_at, raw_text "
            "FROM idp_items WHERE kind IN ('weekly_recap','opinion') "
            "ORDER BY published_at DESC"
        ).fetchall()
        conn.close()
        pending = [dict(r) for r in rows]
    else:
        pending = get_untranslated(list(TRANSLATE_KINDS))

    if not pending:
        console.print("  [dim]Nothing to translate.[/]")
        return

    console.print(f"  {len(pending)} items pending\n")

    total = {"input": 0, "output": 0, "total": 0}
    for item in pending:
        console.print(f"  [{item['kind']}] {item['title'][:80]}...", end=" ")
        parsed, usage = translate_item(item)
        if not parsed:
            console.print("[red]skip[/]")
            continue

        translated_md = parsed.get("summary_md") or ""
        translated_title = parsed.get("title") or item["title"]
        vendors_from_llm = parsed.get("vendors") or []

        save_translation(item["id"], translated_md, translated_title, usage)

        # Merge LLM-detected vendors back into vendors column (union with RSS-derived)
        if vendors_from_llm:
            conn = get_conn()
            row = conn.execute("SELECT vendors FROM idp_items WHERE id=?", (item["id"],)).fetchone()
            existing = json.loads(row["vendors"]) if row and row["vendors"] else []
            merged = list({v: None for v in (*existing, *vendors_from_llm)}.keys())
            conn.execute("UPDATE idp_items SET vendors=? WHERE id=?",
                         (json.dumps(merged, ensure_ascii=False), item["id"]))
            conn.commit()
            conn.close()

        if usage:
            for k in total:
                total[k] += usage.get(k, 0)
        console.print(f"[green]ok[/] (in={usage['input'] if usage else 0})")

    console.print(f"\n  [bold]Tokens:[/] in={total['input']:,} out={total['output']:,} total={total['total']:,}")


def main():
    parser = argparse.ArgumentParser(description="IDP Community pipeline")
    parser.add_argument("--no-translate", action="store_true", help="Skip LLM translation")
    parser.add_argument("--retranslate", action="store_true", help="Re-translate all items")
    args = parser.parse_args()

    load_dotenv()
    init_db()

    run_fetch()
    if not args.no_translate:
        run_translate(retranslate=args.retranslate)


if __name__ == "__main__":
    main()
