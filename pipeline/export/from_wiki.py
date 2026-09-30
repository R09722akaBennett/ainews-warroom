"""Merge the wiki's daily digests and periodic reports into the site data.

Daily digests go to src/data/reports.json. Weekly, monthly and quarterly
notes (notes/weekly, notes/monthly, notes/quarterly) go to
src/data/summaries.json as the industry periods raw_weekly, raw_monthly and
raw_quarterly, which the Trends page and the home page read.

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
import datetime
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "src" / "data" / "reports.json"
SUMMARIES = DATA.with_name("summaries.json")
PERIODS = {"weekly": "raw_weekly", "monthly": "raw_monthly", "quarterly": "raw_quarterly"}
# The company-era KDAN track and competitor records; dropped on every run.
RETIRED_PERIODS = {"weekly", "monthly", "quarterly", "competitor_weekly", "competitor_classify"}
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


def _archive_commit_files(wiki: Path, date: str) -> list[Path]:
    """Return the archive files daily_news.py committed for the note of this date.

    Archive files are named by the article's publish date, which is usually
    the day before the note (the 2026-09-30 note used only 09-29 articles),
    so matching file names to the note date misses them. The run commits its
    archive as "library: news 原文存檔 <date>" just before the note, which
    ties files to notes exactly.
    """
    out = subprocess.run(
        ["git", "-C", str(wiki), "log", "--fixed-strings", f"--grep=news 原文存檔 {date}（",
         "--diff-filter=A", "--name-only", "--format="],
        capture_output=True, text=True, check=False).stdout
    paths = {wiki / line for line in out.splitlines()
             if line.startswith("library/news/") and line.endswith(".md")}
    return sorted(path for path in paths if path.exists())


def _archive_items(wiki: Path, date: str) -> list[dict]:
    items = []
    paths = _archive_commit_files(wiki, date) or sorted((wiki / "library" / "news").glob(f"*/{date} *.md"))
    for path in paths:
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


PICKS_HEADING = "## 📌 今日建議深讀"
ARXIV_WIKILINK = re.compile(r"\[\[(\d{4}\.\d{4,5})\]\]")
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
PICK_LINE = re.compile(r"^(T\d+)\. (.+)$")
# Dropped 2026-10-01; notes written before then still carry it.
REPLY_HINT = re.compile(r"\n*> 回覆「排 T1」[^\n]*")


def _web_content(md: str) -> str:
    """Return the note markdown adapted for the website.

    Obsidian wikilinks mean nothing on the site, so arXiv ids become arXiv
    links and other wikilinks become plain text. The picks section relies on
    single line breaks, which Obsidian and WhatsApp keep but marked joins
    into one paragraph, so each pick becomes a list item with a hard break
    before its reason.
    """
    md = REPLY_HINT.sub("", md)
    md = ARXIV_WIKILINK.sub(lambda m: f"[{m.group(1)}](https://arxiv.org/abs/{m.group(1)})", md)
    md = WIKILINK.sub(lambda m: m.group(2) or m.group(1), md)
    head, sep, picks = md.partition(PICKS_HEADING)
    if not sep:
        return md
    lines: list[str] = []
    for line in picks.split("\n"):
        pick = PICK_LINE.match(line)
        if pick:
            lines.append(f"- **{pick.group(1)}** {pick.group(2)}")
        elif line.startswith("　→") and lines:
            lines[-1] += "  "
            lines.append("  " + line.lstrip("　"))
        else:
            lines.append(line)
    return head + sep + "\n".join(lines).rstrip() + "\n"



COMPANY_WORDS = re.compile(r"(?i)kdan|凱鈿")
COMPANY_LEAD = re.compile(r"凱鈿應關注之重大競品動向[：:]\s*")
COMPANY_SECTION = re.compile(r"\n(?:---\n+)?## KDAN 戰略洞察\n[\s\S]*?(?=\n## |\Z)")


def _retire_company(report: dict) -> dict:
    """Return a company-era report without its KDAN strategy section and branding.

    Reports up to 2026-09-08 came from the company agent and end with a
    "KDAN 戰略洞察" section of product advice; the news analysis before it
    is kept as the archive. Applying this twice changes nothing.
    """
    report = dict(report)
    for key in ("title", "content"):
        report[key] = (report.get(key) or "").replace("KDAN AI 戰情報告", "AI 戰情報告")
    content = COMPANY_SECTION.sub("", report["content"]).rstrip().removesuffix("---").rstrip()
    content = COMPANY_LEAD.sub("", content)
    report["content"] = "\n".join(_drop_company_sentences(line) for line in content.split("\n")
                                  if not _only_company(line)) + "\n"
    return report


def _only_company(line: str) -> bool:
    return bool(COMPANY_WORDS.search(line)) and not _drop_company_sentences(line).strip(" *-#>")


def _drop_company_sentences(line: str) -> str:
    # Trend paragraphs also carry asides such as "對於 KDAN 而言……"; only
    # those sentences go, the news analysis around them stays.
    if not COMPANY_WORDS.search(line):
        return line
    return "".join(part for part in re.split(r"(?<=[。！？])", line) if not COMPANY_WORDS.search(part))


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
                "content": _web_content(data["content"]),
                "newsItems": data.get("newsItems") or [],
                "rawCount": data.get("rawCount") or len(data.get("newsItems") or []),
                "createdAt": data.get("createdAt") or f"{date}T14:30:00",
            }
            if (data.get("tokenUsage") or {}).get("total"):
                report["tokenUsage"] = data["tokenUsage"]
        else:
            _, body = _frontmatter(note.read_text(encoding="utf-8"))
            items = _archive_items(wiki, date)
            report = {"date": date, "title": f"每日 AI 快報 {date}", "content": _web_content(body),
                      "newsItems": items, "rawCount": len(items), "createdAt": f"{date}T14:30:00"}
        report["origin"] = "wiki"
        reports.append(report)
    return reports



def _week_range(name: str) -> tuple[str, str]:
    year, week = name.split("-w")
    monday = datetime.date.fromisocalendar(int(year), int(week), 1)
    return str(monday), str(monday + datetime.timedelta(days=6))


def build_summaries(wiki: Path) -> list[dict]:
    """Return one summaries.json entry per wiki weekly, monthly or quarterly note.

    Weekly notes written before 2026-10-01 have no period_start in their
    frontmatter, so their range comes from the ISO week in the file name.
    """
    out = []
    for kind, period in PERIODS.items():
        for note in sorted((wiki / "notes" / kind).glob("*.md")):
            meta, body = _frontmatter(note.read_text(encoding="utf-8"))
            heading = re.match(r"# (.+)\n", body)
            body = body[heading.end():].lstrip("\n") if heading else body
            if meta.get("period_start"):
                start, end = meta["period_start"], meta["period_end"]
            elif kind == "weekly":
                start, end = _week_range(note.stem)
            else:
                continue
            title = meta.get("title") or (heading.group(1) if heading else note.stem)
            if kind != "weekly":  # the note repeats the title as a quote under the heading
                body = re.sub(r"^(>.*\n)+\n?", "", body)
            entry = {"period": period, "startDate": start, "endDate": end, "title": title,
                     "content": _web_content(body), "createdAt": f"{meta.get('created', end)}T09:00:00",
                     "tags": {k: [] for k in TAG_TYPES}, "origin": "wiki"}
            if meta.get("token_usage"):
                entry["tokenUsage"] = json.loads(meta["token_usage"])
            out.append(entry)
    return out


def merge_summaries(wiki: Path) -> tuple[int, int]:
    """Rewrite summaries.json with fresh wiki entries; return (wiki entries, dropped retired)."""
    existing = json.loads(SUMMARIES.read_text(encoding="utf-8")) if SUMMARIES.exists() else []
    kept = [s for s in existing if s.get("origin") != "wiki" and s.get("period") not in RETIRED_PERIODS]
    fresh = build_summaries(wiki)
    dropped = sum(1 for s in existing if s.get("period") in RETIRED_PERIODS)
    merged = sorted(kept + fresh, key=lambda s: (s.get("endDate") or "", s.get("period")), reverse=True)
    SUMMARIES.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(fresh), dropped


def main() -> None:
    parser = argparse.ArgumentParser(description="把 wiki 日報合併進 src/data/reports.json")
    parser.add_argument("--wiki", default=os.path.expanduser("~/wiki"), help="wiki repo 路徑")
    args = parser.parse_args()

    existing = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    kept = [_retire_company(r) for r in existing if r.get("origin") != "wiki"]
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
    n_summaries, n_dropped = merge_summaries(Path(args.wiki))
    print(f"from_wiki: {n_summaries} wiki periodic reports merged into summaries.json, "
          f"{n_dropped} retired entries dropped")


if __name__ == "__main__":
    main()
