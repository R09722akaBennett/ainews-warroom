"""Store the labs' X posts in knowledge DB (source x:lab_posts), raw post included."""

from __future__ import annotations

import json
import os
import urllib.request

API = os.getenv("KNOWLEDGE_API", "http://127.0.0.1:8000")


def ingest_posts(lab_key: str, items: list[dict]) -> dict:
    """Send X items to knowledge-api; return {"created", "skipped", "failed"}.

    Non-X items are ignored. Failures are counted, never raised, so the
    labs run continues when knowledge-api is down.
    """
    stats = {"created": 0, "skipped": 0, "failed": 0}
    token = os.getenv("INGEST_API_TOKEN")
    for it in items:
        if not it.get("raw") or not token:
            continue
        msg = {"id": f"x-{it['raw']['id']}", "title": it["title"], "url": it["url"],
               "author": f"@{it['handle']}", "published_at": it.get("published_at"),
               "sections": [{"title": it["title"], "category": lab_key, "text": it["content"]}],
               "lab": lab_key, "raw": it["raw"]}
        req = urllib.request.Request(f"{API}/ingest/email", method="POST",
                                     data=json.dumps({"source_key": "x:lab_posts", "message": msg}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status = json.load(r).get("status")
            stats["skipped" if status == "skipped" else "created"] += 1
        except Exception:  # noqa: BLE001
            stats["failed"] += 1
    return stats
