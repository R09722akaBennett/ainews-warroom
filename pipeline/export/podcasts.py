"""Export the collected podcast episodes to the site.

Writes src/data/podcasts.json (the list: no transcripts) and
src/data/podcasts/<slug>.json (one full episode each) from the cache that
python -m podcasts fills. The audio URL is not exported: Substack's audio
links carry the subscriber's token.

Usage:
    cd pipeline
    uv run --no-sync python -m export.podcasts
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from export.translate import Translator

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "pipeline" / "data" / "podcasts"
INDEX = ROOT / "src" / "data" / "podcasts.json"
EPISODES = ROOT / "src" / "data" / "podcasts"
LIST_KEYS = ("slug", "show", "title", "subtitle", "date", "url", "youtube", "duration", "image", "guests")


def english_summary(summary: dict, translator: Translator) -> dict | None:
    """Return the summary with one_liner, topics, insights and guest intros in English, or None.

    Quotes already carry both languages and are copied as they are. None
    when any text could not be translated, so a page never mixes languages.
    """
    texts = [summary.get("one_liner", "")]
    for key in ("topics", "insights"):
        for t in summary.get(key, []):
            texts += [t.get("title", ""), t.get("body", "")]
    texts += [g.get("intro", "") for g in summary.get("guests", [])]
    out = translator.many(texts, "en")
    if any(x is None for x in out):
        return None
    it = iter(out)
    en = {**summary, "one_liner": next(it)}
    for key in ("topics", "insights"):
        en[key] = [{**t, "title": next(it), "body": next(it)} for t in summary.get(key, [])]
    en["guests"] = [{**g, "intro": next(it)} for g in summary.get("guests", [])]
    return en


def main() -> None:
    EPISODES.mkdir(parents=True, exist_ok=True)
    eps = sorted((json.loads(f.read_text(encoding="utf-8")) for f in CACHE.glob("*.json")),
                 key=lambda e: e["date"], reverse=True)
    translator = Translator()
    index = []
    for e in eps:
        s = e.get("summary") or {}
        full = {k: e.get(k) for k in (*LIST_KEYS, "intro", "we_discuss", "chapters", "transcript", "tokenUsage")}
        full["summary"] = s
        en = english_summary(s, translator) if s else None
        if en:
            full["en"] = {"summary": en}
        (EPISODES / f"{e['slug']}.json").write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
        index.append({**{k: e.get(k) for k in LIST_KEYS}, "one_liner": s.get("one_liner", ""),
                      "topics": [t.get("title") for t in s.get("topics", [])],
                      "words": sum(len(t["text"].split()) for c in e["transcript"] for t in c["turns"]),
                      "tokenUsage": e.get("tokenUsage"),
                      **({"en": {"one_liner": en["one_liner"], "topics": [t["title"] for t in en["topics"]]}}
                         if en else {})})
    keep = {f"{e['slug']}.json" for e in eps}
    for f in EPISODES.glob("*.json"):
        if f.name not in keep:
            f.unlink()
    INDEX.write_text(json.dumps({"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 "episodes": index}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"podcasts: {len(index)} episodes exported, {sum('en' in i for i in index)} in English")
    translator.report("podcasts")


if __name__ == "__main__":
    main()
