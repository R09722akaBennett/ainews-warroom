"""Export the frontier-lab tracker to src/data/labs.json and summaries.json.

Only the labs' official X posts are listed; the Google News items collected
earlier stay in warroom.db but are not shown.

Writes only lab data: on bennett-hub warroom.db holds only the lab-tracker
era, so the other site files must not be rebuilt from it.

labs.json holds the lab list with display attributes (from labs.config) and
every relevant, classified item. Daily briefs, weekly reports and
classification token records (periods labs_daily, labs_weekly and
labs_classify) are merged into summaries.json, replacing earlier copies of
those three periods only.

Usage:
    cd pipeline
    uv run --no-sync python -m export.labs
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from labs.config import LABS
from db.connection import get_conn, init_db
from export.translate import Translator

DATA = Path(__file__).resolve().parents[2] / "src" / "data"
PERIODS = ("labs_daily", "labs_weekly", "labs_classify")


def _merge_threads(items: list[dict]) -> list[dict]:
    """Return items with each thread folded into one post and duplicates and replies dropped.

    The September 2026 backfill stored every part of a thread as its own post
    (61 groups posted by one lab within the same second), StepFun's Step Code
    thread twice under different ids, and 23 replies to other accounts. Newer
    posts arrive merged from labs/x_source.py. Merged parts keep their URLs in
    "aliases" so brief links to any part still find the post.
    """
    items = [i for i in items if not i["content"].lstrip().startswith("@")]
    groups: dict[tuple, list[dict]] = {}
    for i in items:
        groups.setdefault((i["lab"], (i["publishedAt"] or i["url"])[:19]), []).append(i)
    out, seen = [], set()
    for group in groups.values():
        group.sort(key=lambda i: int(i["url"].rsplit("/", 1)[-1]) if i["url"].rsplit("/", 1)[-1].isdigit() else 0)
        head = dict(group[0])
        texts = []
        for part in group:
            if part["content"] not in texts:
                texts.append(part["content"])
        head["content"] = "\n\n".join(texts)
        head["aliases"] = [p["url"] for p in group[1:]]
        key = (head["lab"], head["content"])
        if key in seen:
            continue
        seen.add(key)
        out.append(head)
    return sorted(out, key=lambda i: (i["date"], i["publishedAt"] or ""), reverse=True)


def main() -> None:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, company, title, url, source, published_at, category, summary, content FROM competitor_items "
        "WHERE ai_related = 1 AND category != 'pending' AND source LIKE 'X @%' "
        "ORDER BY date DESC, company, id").fetchall()
    sums = conn.execute(
        f"SELECT period, start_date, end_date, title, content, tags, token_usage, created_at "
        f"FROM periodic_summaries WHERE period IN ({','.join('?' * len(PERIODS))}) "
        f"ORDER BY start_date DESC", PERIODS).fetchall()
    conn.close()

    labs = [{"key": k, "name": v["name"], "tier": v["tier"], "region": v["region"], "openness": v["openness"]}
            for k, v in LABS.items()]
    # Posts stored before x_source unescaped text keep X's HTML escaping; unescape on the way out.
    items = _merge_threads([{"date": r["date"], "lab": r["company"], "title": html.unescape(r["title"]),
                             "url": r["url"], "source": r["source"], "publishedAt": r["published_at"],
                             "category": r["category"], "summary": r["summary"],
                             "content": html.unescape(r["content"] or "")}
                            for r in rows if r["company"] in LABS])
    translator = Translator()
    for item, summary in zip(items, translator.many([i["summary"] for i in items], "en")):
        if summary:
            item["en"] = {"summary": summary}
    (DATA / "labs.json").write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "labs": labs, "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    path = DATA / "summaries.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    kept = [s for s in existing if s.get("period") not in PERIODS]
    fresh = []
    for r in sums:
        entry = {"period": r["period"], "startDate": r["start_date"], "endDate": r["end_date"], "title": r["title"],
                 "content": r["content"], "createdAt": r["created_at"],
                 "tags": json.loads(r["tags"]) if r["tags"] else {}}
        if r["token_usage"]:
            entry["tokenUsage"] = json.loads(r["token_usage"])
        fresh.append(entry)
    briefs = [s for s in fresh if s["period"] != "labs_classify" and s["content"]]
    titles = translator.many([s["title"] for s in briefs], "en")
    contents = translator.many([s["content"] for s in briefs], "en")
    for s, title, content in zip(briefs, titles, contents):
        if title and content:
            s["en"] = {"title": title, "content": content}
    path.write_text(json.dumps(kept + fresh, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"labs: {len(items)} items across {len({i['lab'] for i in items})} labs; "
          f"{sum(s['period'] == 'labs_weekly' for s in fresh)} weekly reports merged into summaries.json")
    translator.report("labs")


if __name__ == "__main__":
    main()
