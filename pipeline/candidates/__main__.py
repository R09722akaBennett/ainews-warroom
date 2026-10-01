"""Collect and score wide-source candidates for the day.

Since 2026-10-01 the wiki daily digest (16:30) reads each day's output and
takes the items Jev rates important at 0.75 or more, deduplicated, as extra
material; this job runs at 16:05 so the file is ready.

Usage:
    cd pipeline
    uv run python -m candidates [--wiki ~/wiki] [--no-jev]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date as date_cls, timedelta
from pathlib import Path

from candidates import config, jev
from candidates.collect import collect, normalize_url

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "candidates"


def _curated(wiki: Path, day: str, back_days: int = 3):
    """Return (today's digest items with cited flag, items covered in the last few days)."""
    today, recent = [], []
    d0 = date_cls.fromisoformat(day)
    for n in range(back_days + 1):
        side = wiki / "notes" / "news" / f"{(d0 - timedelta(days=n)).isoformat()}.json"
        if not side.exists():
            continue
        data = json.loads(side.read_text(encoding="utf-8"))
        cited = {int(x) for x in re.findall(r"ref-(\d+)", data.get("content", ""))}
        for i, item in enumerate(data.get("newsItems") or []):
            entry = {**item, "key": normalize_url(item.get("url", ""))}
            recent.append(entry)
            if n == 0:
                today.append({**entry, "cited": i in cited, "snippet": ""})
    return today, recent


def main() -> int:
    ap = argparse.ArgumentParser(description="收集廣來源候選新聞並用 Jev 打分（影子模式，不影響日報）")
    ap.add_argument("--wiki", default=os.path.expanduser("~/wiki"), help="wiki repo 路徑")
    ap.add_argument("--no-jev", action="store_true", help="只收集與去重，不呼叫 Jev")
    args = ap.parse_args()

    day = date_cls.today().isoformat()
    items, stats = collect(day)
    print(f"candidates: fetched {stats['fetched']}, kept {stats['kept']}, dropped {stats['dropped']}")
    for err in stats["errors"]:
        print(f"candidates: source error {err}")
    if stats["fetched"] == 0:
        print("candidates: every source returned nothing", file=sys.stderr)
        return 1

    curated_today, curated_recent = _curated(Path(args.wiki), day)
    known = {c["key"] for c in curated_recent}
    for it in items:
        it["in_curated"] = it["key"] in known

    result = {"date": day, "stats": stats, "jev": {"status": "skipped"}}
    if args.no_jev or not jev.available():
        reason = "--no-jev" if args.no_jev else "TYPESAFE_API_KEY not set"
        print(f"candidates: Jev skipped ({reason}); candidates saved unscored")
        result["jev"]["reason"] = reason
    else:
        interests = os.environ.get("USER_INTERESTS", "AI agents, LLM infrastructure and open models")
        result["jev"] = jev.score(items, interests)
        result["jev"]["model"] = config.JEV_MODEL
        result["calibration"] = jev.score(curated_today, interests)
        print(f"candidates: Jev {result['jev']}")
        top = sorted((i for i in items if i.get("jev")), key=lambda i: i["jev"]["important"] or 0, reverse=True)
        head = top[: config.TOP_FOR_DEDUP]
        result["same_event"] = {
            "vs_curated": jev.same_event(head, curated_recent, field="dup_of"),
            "within_day": jev.same_event(head, None, field="dup_within"),
        }
        if result["jev"]["status"] == "degraded":
            print("candidates: Jev stage degraded; a live run would use curated feeds only")

    items.sort(key=lambda i: ((i.get("jev") or {}).get("important") or 0), reverse=True)
    result["candidates"] = items
    result["curated"] = curated_today
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{day}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"candidates: wrote {path.relative_to(OUT_DIR.parents[1])} ({len(items)} candidates, "
          f"{len(curated_today)} curated for calibration)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
