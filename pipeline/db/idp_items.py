"""IDP Community items CRUD."""

from __future__ import annotations

import json

from db.connection import get_conn


def upsert_idp_item(item: dict) -> tuple[int, bool]:
    """Insert or update an IDP item by guid. Returns (row_id, is_new)."""
    conn = get_conn()
    row = conn.execute("SELECT id FROM idp_items WHERE guid = ?", (item["guid"],)).fetchone()
    is_new = row is None

    vendors_json = json.dumps(item.get("vendors", []), ensure_ascii=False)
    categories_json = json.dumps(item.get("categories", []), ensure_ascii=False)

    if is_new:
        cur = conn.execute(
            """INSERT INTO idp_items
               (guid, url, title, kind, published_at, vendors, categories, raw_html, raw_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["guid"], item["url"], item["title"], item["kind"],
                item.get("published_at"), vendors_json, categories_json,
                item.get("raw_html", ""), item.get("raw_text", ""),
            ),
        )
        row_id = cur.lastrowid
    else:
        row_id = row["id"]
        conn.execute(
            """UPDATE idp_items SET
               url=?, title=?, kind=?, published_at=?, vendors=?, categories=?,
               raw_html=?, raw_text=?, updated_at=datetime('now')
               WHERE id=?""",
            (
                item["url"], item["title"], item["kind"], item.get("published_at"),
                vendors_json, categories_json,
                item.get("raw_html", ""), item.get("raw_text", ""), row_id,
            ),
        )
    conn.commit()
    conn.close()
    return row_id, is_new


def save_translation(item_id: int, translated_md: str, translated_title: str | None, token_usage: dict | None):
    conn = get_conn()
    conn.execute(
        "UPDATE idp_items SET translated_md=?, translated_title=?, token_usage=?, updated_at=datetime('now') WHERE id=?",
        (translated_md, translated_title, json.dumps(token_usage) if token_usage else None, item_id),
    )
    conn.commit()
    conn.close()


def get_untranslated(kinds: list[str] | None = None) -> list[dict]:
    """Items that need LLM translation."""
    conn = get_conn()
    q = "SELECT id, guid, url, title, kind, published_at, raw_text FROM idp_items WHERE (translated_md IS NULL OR translated_md = '')"
    params: list = []
    if kinds:
        q += " AND kind IN (" + ",".join("?" * len(kinds)) + ")"
        params.extend(kinds)
    q += " ORDER BY published_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_idp_items() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, guid, url, title, kind, published_at, vendors, categories,
                  translated_md, translated_title, token_usage
           FROM idp_items ORDER BY published_at DESC, id DESC"""
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["vendors"] = json.loads(d["vendors"]) if d.get("vendors") else []
        d["categories"] = json.loads(d["categories"]) if d.get("categories") else []
        if d.get("token_usage"):
            try:
                d["token_usage"] = json.loads(d["token_usage"])
            except Exception:
                d["token_usage"] = None
        out.append(d)
    return out
