"""Export the frontier-lab tracker to src/data/labs.json and summaries.json.

Writes only lab data. The general `python -m export` rebuilds every JSON
file from warroom.db, and on bennett-hub that database only holds data from
2026-10-01 on, so running it there would wipe the site's history.

labs.json holds the lab list with display attributes (from
competitor.config) and every relevant, classified item. Weekly reports and
token usage records (periods labs_weekly and labs_classify) are merged into
summaries.json, replacing earlier copies of those two periods only.

Usage:
    cd pipeline
    uv run python -m export.labs
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from competitor.config import LABS
from db.connection import get_conn, init_db

DATA = Path(__file__).resolve().parents[2] / "src" / "data"
PERIODS = ("labs_weekly", "labs_classify")


def main() -> None:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, company, title, url, source, published_at, category, summary FROM competitor_items "
        "WHERE ai_related = 1 AND category != 'pending' ORDER BY date DESC, company, id").fetchall()
    sums = conn.execute(
        f"SELECT period, start_date, end_date, title, content, tags, token_usage, created_at "
        f"FROM periodic_summaries WHERE period IN ({','.join('?' * len(PERIODS))}) "
        f"ORDER BY start_date DESC", PERIODS).fetchall()
    conn.close()

    labs = [{"key": k, "name": v["name"], "tier": v["tier"], "region": v["region"], "openness": v["openness"]}
            for k, v in LABS.items()]
    items = [{"date": r["date"], "lab": r["company"], "title": r["title"], "url": r["url"], "source": r["source"],
              "publishedAt": r["published_at"], "category": r["category"], "summary": r["summary"]}
             for r in rows if r["company"] in LABS]
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
    path.write_text(json.dumps(kept + fresh, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"labs: {len(items)} items across {len({i['lab'] for i in items})} labs; "
          f"{sum(s['period'] == 'labs_weekly' for s in fresh)} weekly reports merged into summaries.json")


if __name__ == "__main__":
    main()
