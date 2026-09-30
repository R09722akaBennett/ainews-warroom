"""Merge the wiki's daily digests into src/data/reports.json.

The wiki pipeline (bennett-hub ~/wiki/tools/daily_news.py) writes
notes/news/YYYY-MM-DD.md plus a .json sidecar with ref-numbered content,
newsItems and token usage. Reports this module produces carry
origin="wiki" and are rebuilt on every run; reports without that marker
(the old in-repo agent, up to 2026-09-08) are left untouched, and a wiki
date that already has one of them is skipped.

Notes written before sidecars existed (2026-09-09 .. 2026-09-30) are
exported from the markdown alone, with newsItems rebuilt from that day's
library/news archive, so they list sources but have no ref-N links.

Usage:
    cd pipeline
    uv run python -m export.from_wiki [--wiki ~/wiki]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "src" / "data" / "reports.json"
SOURCE_NAMES = {"smol": "smol.ai", "tldr": "TLDR AI", "techcrunch": "TechCrunch", "importai": "Import AI"}
TAG_TYPES = {"companies": ("org", "company"), "models": ("model",), "topics": ("concept", "method")}
# Too generic to be useful as a tag; they top every day's counts.
TAG_STOPWORDS = {"ai", "artificial intelligence", "llm", "llms", "large language models", "ai models"}
TAGS_PER_KIND = 8


def _frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip().strip('"')
    return meta, body.lstrip("\n")


def _archive_items(wiki: Path, date: str) -> list[dict]:
    items = []
    for path in sorted((wiki / "library" / "news").glob(f"*/{date} *.md")):
        meta, _ = _frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("url"):
            title = meta.get("title", "")
            try:
                title = json.loads(f'"{title}"') if "\\u" in title else title
            except json.JSONDecodeError:
                pass
            items.append({"url": meta["url"], "title": title,
                          "source": SOURCE_NAMES.get(path.parent.name, path.parent.name)})
    return items


def _slug(name: str) -> str:
    return re.sub(r"\s+", "-", name.strip().lower())


def _tags_by_date(dates: list[str]) -> dict[str, dict]:
    """Return {date: {companies, models, topics}} from knowledge DB entities.

    Uses the per-document LLM extraction that knowledge-api already stored,
    so no model call happens here. Missing dates (extraction not finished
    yet) simply get empty tags and are filled on the next run.
    """
    if not dates:
        return {}
    date_list = ",".join(f"'{d}'" for d in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    sql = f"""
      select coalesce(json_agg(row_to_json(t)), '[]') from (
        select (d.created_at at time zone 'Asia/Taipei')::date::text as date,
               coalesce(m.canonical, e->>'canonical_name') as name, e->>'type' as type
        from knowledge.extractions x
        join knowledge.documents d on d.id = x.document_id
        join knowledge.sources s on s.id = d.source_id
        cross join jsonb_array_elements(x.raw_json->'entities') e
        left join knowledge.entity_merge_map m on m.member_lower = lower(e->>'canonical_name')
        where s.source_key like 'rss:%'
          and (d.created_at at time zone 'Asia/Taipei')::date in ({date_list})
          and coalesce((e->>'salience')::numeric, 0) >= 0.6) t"""
    out = subprocess.run(
        ["docker", "exec", "-i", "postgres", "psql", "-U", "postgres", "-d", "kdan", "-At", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True, check=True).stdout.strip()
    counters: dict[str, dict[str, Counter]] = {}
    for row in json.loads(out or "[]"):
        name = (row.get("name") or "").strip()
        if not name or name.lower() in TAG_STOPWORDS:
            continue
        for kind, types in TAG_TYPES.items():
            if row.get("type") in types:
                counters.setdefault(row["date"], {k: Counter() for k in TAG_TYPES})[kind][_slug(name)] += 1
    return {d: {k: [n for n, _ in c.most_common(TAGS_PER_KIND)] for k, c in kinds.items()}
            for d, kinds in counters.items()}


def build_reports(wiki: Path) -> list[dict]:
    reports = []
    for note in sorted((wiki / "notes" / "news").glob("????-??-??.md")):
        date = note.stem
        sidecar = note.with_suffix(".json")
        if sidecar.exists():
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            report = {
                "date": date,
                "title": data.get("title") or f"每日 AI 快報 {date}",
                "content": data["content"],
                "newsItems": data.get("newsItems") or [],
                "rawCount": data.get("rawCount") or len(data.get("newsItems") or []),
                "createdAt": data.get("createdAt") or f"{date}T14:30:00",
            }
            if (data.get("tokenUsage") or {}).get("total"):
                report["tokenUsage"] = data["tokenUsage"]
        else:
            _, body = _frontmatter(note.read_text(encoding="utf-8"))
            items = _archive_items(wiki, date)
            report = {"date": date, "title": f"每日 AI 快報 {date}", "content": body,
                      "newsItems": items, "rawCount": len(items), "createdAt": f"{date}T14:30:00"}
        report["origin"] = "wiki"
        reports.append(report)
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="把 wiki 日報合併進 src/data/reports.json")
    parser.add_argument("--wiki", default=os.path.expanduser("~/wiki"), help="wiki repo 路徑")
    args = parser.parse_args()

    existing = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    kept = [r for r in existing if r.get("origin") != "wiki"]
    taken = {r["date"] for r in kept}
    fresh = [r for r in build_reports(Path(args.wiki)) if r["date"] not in taken]
    tags = _tags_by_date([r["date"] for r in fresh])
    for r in fresh:
        r["tags"] = tags.get(r["date"], {k: [] for k in TAG_TYPES})
    merged = sorted(kept + fresh, key=lambda r: r["date"], reverse=True)
    DATA.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"from_wiki: {len(fresh)} wiki reports merged, {len(kept)} kept, "
          f"{sum(1 for r in fresh if r['newsItems'])} with sources, "
          f"{sum(1 for r in fresh if any(r['tags'].values()))} with tags")


if __name__ == "__main__":
    main()
