"""Export the reading shelf (newsletters that explain rather than report) to src/data/reading.json.

The shelf holds the newsletters ingest_newsletters.py and
ingest_daily_dose.py on bennett-hub send to knowledge DB from Gmail. Berkeley RDI also
feeds the weekly digest; it is listed here because readers come back to it.
Each item carries its section titles and up to three section summaries, or
the opening of the text while LLM extraction has not run yet. Items link to
the original post (canonical_url; Daily Dose URLs are resolved from its blog
by title). Notion pages are not linked: they are private to the workspace
owner. Instead each item carries its sections with the same summary and
takeaways knowledge-api writes to Notion, and the site renders them as
/reading/<slug>.

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

from export.translate import Translator

DATA = Path(__file__).resolve().parents[2] / "src" / "data" / "reading.json"
SOURCES = {
    "gmail:bytebytego": {"name": "ByteByteGo", "cadence": "每週約 5 封", "lang": "en"},
    "gmail:daily_dose_of_ds": {"name": "Daily Dose of DS", "cadence": "每週 1 到 2 封", "lang": "en"},
    "gmail:berkeley_rdi": {"name": "Berkeley RDI", "cadence": "每週三", "lang": "en"},
    "gmail:explainthis": {"name": "ExplainThis", "cadence": "隔週日", "lang": "zh"},
    # Latent Space essays only: AINews issues feed the daily digest and the
    # podcast episodes have their own page, so ingest_newsletters.py keeps
    # the mails whose post is a Substack "newsletter".
    "gmail:latent_space": {"name": "Latent Space", "cadence": "不定期，每週 0 到 2 篇", "lang": "en"},
    "gmail:the_batch": {"name": "The Batch", "cadence": "每週三", "lang": "en"},
    "gmail:aihao": {"name": "愛好 AI Engineer 電子報", "cadence": "不定期", "lang": "zh"},
    "gmail:datatalks": {"name": "DataTalks.Club Weekly", "cadence": "每週", "lang": "en"},
}
# No recorded reason for 120 days; chosen by trial.
SINCE_DAYS = 120
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")

SQL = """
select coalesce(json_agg(row_to_json(t) order by t.published desc), '[]') from (
  select d.id::text as doc_id, s.source_key as source, d.title, d.canonical_url as url,
         to_char(coalesce(d.published_at, d.created_at), 'YYYY-MM-DD') as published,
         (select json_agg(sec.title order by sec.section_index) from knowledge.sections sec
            where sec.document_id = d.id and sec.title is not null
              and sec.document_version_id = v.id and %(not_sponsor)s) as headings,
         (select string_agg(x.summary, ' ' order by x.section_index) from (
            select sec.summary, sec.section_index from knowledge.sections sec
            where sec.document_id = d.id and sec.document_version_id = v.id and sec.summary is not null
              and %(not_sponsor)s
            order by sec.section_index limit 3) x) as summary,
         (select json_agg(json_build_object('title', sec.title, 'category', sec.category, 'summary', sec.summary,
                                            'takeaways', coalesce(sec.key_takeaways, '[]'::jsonb))
                          order by sec.section_index)
            from knowledge.sections sec
            where sec.document_id = d.id and sec.document_version_id = v.id and %(not_sponsor)s
              and sec.section_type = 'content') as sections,
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
"""
# ByteByteGo opens most issues with a "(Sponsored)" section; it is not reading material.
NOT_SPONSOR = "coalesce(sec.title, '') !~* 'sponsor'"
SQL = SQL.replace("%(not_sponsor)s", NOT_SPONSOR) % (", ".join(f"'{k}'" for k in SOURCES), SINCE_DAYS)


def _clean_heading(h: str | None) -> str:
    return re.sub(r"\]\(https?://\S*$", "", MD_LINK.sub(r"\1", h or "")).lstrip("[").strip()


def _slug(title: str, doc_id: str) -> str:
    """Return a URL slug that stays the same across exports: title words plus the document id prefix."""
    words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60].rstrip("-")
    return f"{words}-{doc_id[:8]}" if words else doc_id[:8]


def add_chinese(items: list[dict], translator: Translator) -> int:
    """Put Chinese summary, headings and sections under item["zh"]; return how many items got them.

    Titles stay in English: the newsletters are known by their English
    titles and the Chinese page shows them as the source wrote them.
    """
    texts: list[str] = []
    for it in items:
        texts.append(it["summary"])
        texts += it["headings"]
        for s in it["sections"]:
            texts += [s["title"] or "", s["summary"], *s["takeaways"]]
    out = iter(translator.many(texts, "zh"))
    done = 0
    for it in items:
        zh = {"summary": next(out), "headings": [next(out) for _ in it["headings"]], "sections": []}
        for s in it["sections"]:
            zh["sections"].append({"title": next(out) or None, "summary": next(out),
                                   "takeaways": [next(out) for _ in s["takeaways"]]})
        texts_zh = [zh["summary"], *zh["headings"]] + [x for s in zh["sections"] for x in (s["summary"], *s["takeaways"])]
        if all(x is not None for x in texts_zh):
            it["zh"] = zh
            done += 1
    return done


def main() -> None:
    out = subprocess.run(
        ["docker", "exec", "-i", "postgres", "psql", "-U", "postgres", "-d", "kdan", "-At", "-v", "ON_ERROR_STOP=1"],
        input=SQL, capture_output=True, text=True, check=True).stdout.strip()
    rows = json.loads(out or "[]")
    items = []
    for r in rows:
        headings = [_clean_heading(h) for h in (r.get("headings") or []) if h and h != r["title"]]
        sections = [{"title": _clean_heading(x.get("title")) or None,
                     "category": x.get("category") if x.get("category") not in (None, "article") else None,
                     "summary": x.get("summary") or "",
                     "takeaways": [t for t in (x.get("takeaways") or []) if t]}
                    for x in (r.get("sections") or [])]
        items.append({"id": _slug(r["title"], r["doc_id"]), "source": r["source"], "title": r["title"],
                      "url": r.get("url"), "date": r["published"], "sections": sections,
                      "summary": r.get("summary") or r.get("opening") or "",
                      "summarised": bool(r.get("summary")), "headings": headings[:8]})
    translator = Translator()
    translated = add_chinese(items, translator)
    DATA.write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": [{"key": k, **v} for k, v in SOURCES.items()],
        "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {SOURCES[k]["name"]: sum(i["source"] == k for i in items) for k in SOURCES}
    print(f"reading: {len(items)} items {counts}, {translated} in Chinese")
    translator.report("reading")


if __name__ == "__main__":
    main()
