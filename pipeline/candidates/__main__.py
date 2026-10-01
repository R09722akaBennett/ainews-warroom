"""Collect and score wide-source candidates for the day.

The wiki daily digest (18:00) reads each day's output and takes the items
Jev rates important at 0.75 or more, deduplicated, as extra material; this
job runs at 17:35 so the file is ready. Without --live the run only prints
what it would do and makes no network call, because Jev is billed per call.

Usage:
    cd pipeline
    uv run --no-sync python -m candidates                  # dry-run
    uv run --no-sync python -m candidates --live [--wiki ~/wiki] [--no-jev]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date as date_cls, timedelta
from pathlib import Path

import config as pipeline_config
from candidates import config, jev
from candidates.collect import collect, normalize_url

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "candidates"


def _curated(wiki: Path, day: str, back_days: int = 3):
    """Read the curated digests of day and the back_days before it.

    Returns:
        Today's digest items, each flagged with whether the digest cites it,
        and every item of the window, for same-event checks.
    """
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


def dry_run(day: str, wiki: Path, no_jev: bool) -> None:
    """Print what a live run would do; reads nothing over the network."""
    feeds = [n for n in config.RSS_FEED_NAMES if n in pipeline_config.RSS_FEEDS]
    print(f"[dry-run] Will fetch the Hacker News top {pipeline_config.HACKERNEWS_TOP_N}, {len(feeds)} RSS feeds, "
          f"Lobsters tags {', '.join(pipeline_config.LOBSTERS_AI_TAGS)} and "
          f"{len(pipeline_config.GOOGLE_NEWS_QUERIES)} Google News queries")
    print(f"[dry-run] Will drop items older than {config.FRESH_HOURS}h and URLs seen in the last "
          f"{config.CROSS_DAY_DAYS} days (warroom.db and knowledge DB)")
    if no_jev or not jev.available():
        reason = "--no-jev" if no_jev else "TYPESAFE_API_KEY is not set"
        print(f"[dry-run] Will skip Jev ({reason}) and save the candidates unscored")
    else:
        print(f"[dry-run] Will score every candidate with {config.JEV_MODEL} ({config.JEV_WORKERS} workers, "
              f"{config.JEV_DEADLINE_S}s deadline) and check the top {config.TOP_FOR_DEDUP} for repeated events")
    print(f"[dry-run] Will compare with the digests in {wiki / 'notes' / 'news'} and write "
          f"{OUT_DIR.relative_to(OUT_DIR.parents[1]) / (day + '.json')}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="收集廣來源候選新聞並用 Jev 打分，18:00 日報取用當天結果（預設 dry-run，只列出會做的事）")
    ap.add_argument("--live", action="store_true", help="真的抓取來源、呼叫 Jev 並寫出結果（會產生費用）")
    ap.add_argument("--wiki", default=os.path.expanduser("~/wiki"), help="wiki repo 路徑")
    ap.add_argument("--no-jev", action="store_true", help="只收集與去重，不呼叫 Jev")
    args = ap.parse_args()

    day = date_cls.today().isoformat()
    if not args.live:
        dry_run(day, Path(args.wiki), args.no_jev)
        return 0
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
            print("candidates: Jev stage degraded; unscored candidates fall below the digest's threshold "
                  "and are left out")

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
