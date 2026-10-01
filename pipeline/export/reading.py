"""Export the reading shelf (newsletters that explain rather than report) to src/data/reading.json.

The shelf holds ByteByteGo, Daily Dose of DS, ExplainThis and Berkeley RDI's
Agentic AI Weekly as ingested into knowledge DB from Gmail. Berkeley RDI also
feeds the weekly digest; it is listed here because readers come back to it.
Each item carries its section titles and up to three section summaries, or
the opening of the text while LLM extraction has not run yet. Items link to
the original post (canonical_url; Daily Dose URLs are resolved from its blog
by title). Notion pages are not linked: they are private to the workspace
owner and the site is for reading the originals.

Usage:
    cd pipeline
    uv run --no-sync python -m export.reading
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "src" / "data" / "reading.json"
SOURCES = {
    "gmail:bytebytego": {"name": "ByteByteGo", "cadence": "每週約 5 封", "lang": "en"},
    "gmail:daily_dose_of_ds": {"name": "Daily Dose of DS", "cadence": "每週 1 到 2 封", "lang": "en"},
    "gmail:berkeley_rdi": {"name": "Berkeley RDI", "cadence": "每週三", "lang": "en"},
    "gmail:explainthis": {"name": "ExplainThis", "cadence": "隔週日", "lang": "zh"},
}
SINCE_DAYS = 120
# ByteByteGo opens most issues with a "(Sponsored)" section; it is not reading material.
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")

SQL = """
select coalesce(json_agg(row_to_json(t) order by t.published desc), '[]') from (
  select s.source_key as source, d.title, d.canonical_url as url,
         to_char(coalesce(d.published_at, d.created_at), 'YYYY-MM-DD') as published,
         (select json_agg(sec.title order by sec.section_index) from knowledge.sections sec
            where sec.document_id = d.id and sec.title is not null
              and sec.document_version_id = v.id and %(not_sponsor)s) as headings,
         (select string_agg(x.summary, ' ' order by x.section_index) from (
            select sec.summary, sec.section_index from knowledge.sections sec
            where sec.document_id = d.id and sec.document_version_id = v.id and sec.summary is not null
              and %(not_sponsor)s
            order by sec.section_index limit 3) x) as summary,
         (select left(regexp_replace(sec.raw_text, '\\s+', ' ', 'g'), 400) from knowledge.sections sec
            where sec.document_id = d.id and sec.document_version_id = v.id and %(not_sponsor)s
            order by sec.section_index limit 1) as opening
  from knowledge.documents d
  join knowledge.sources s on s.id = d.source_id
  join lateral (select id from knowledge.document_versions where document_id = d.id
                order by version_no desc limit 1) v on true
  where s.source_key in (%s)
    and coalesce(d.published_at, d.created_at) >= now() - interval '%d days'
) t
""".replace("%(not_sponsor)s", "coalesce(sec.title, '') !~* 'sponsor'") % (", ".join(f"'{k}'" for k in SOURCES), SINCE_DAYS)


def main() -> None:
    out = subprocess.run(
        ["docker", "exec", "-i", "postgres", "psql", "-U", "postgres", "-d", "kdan", "-At", "-v", "ON_ERROR_STOP=1"],
        input=SQL, capture_output=True, text=True, check=True).stdout.strip()
    rows = json.loads(out or "[]")
    items = []
    for r in rows:
        headings = [re.sub(r"\]\(https?://\S*$", "", MD_LINK.sub(r"\1", h)).lstrip("[").strip()
                    for h in (r.get("headings") or []) if h and h != r["title"]]
        items.append({"source": r["source"], "title": r["title"], "url": r.get("url"), "date": r["published"],
                      "summary": r.get("summary") or r.get("opening") or "",
                      "summarised": bool(r.get("summary")), "headings": headings[:8]})
    DATA.write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": [{"key": k, **v} for k, v in SOURCES.items()],
        "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {SOURCES[k]["name"]: sum(i["source"] == k for i in items) for k in SOURCES}
    print(f"reading: {len(items)} items {counts}")


if __name__ == "__main__":
    main()
