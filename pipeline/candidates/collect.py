"""Collect wide-source candidates and drop repeats and stale items."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import config as pipeline_config
import sources.rss_feeds as rss_module
from candidates import config
from db import get_recent_urls, init_db, save_raw_items
from sources.google_news import fetch_google_news
from sources.hackernews import fetch_hackernews
from sources.lobsters import fetch_lobsters

TRACKING = re.compile(r"^(utm_|ref$|ref_src$|fbclid$|gclid$|mc_|cmpid$|source$)")


def normalize_url(url: str) -> str:
    """Return a comparison key: lowercase host without www, no tracking query, no fragment."""
    parts = urlsplit((url or "").strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not TRACKING.match(k.lower())])
    return urlunsplit((parts.scheme.lower() or "https", host, parts.path.rstrip("/"), query, ""))


def _title_key(title: str) -> frozenset:
    return frozenset(w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 2)


def _similar(a: frozenset, b: frozenset) -> bool:
    # Jaccard similarity of title words; 0.8 catches the same headline
    # reworded by an aggregator. No recorded reason for 0.8; chosen by trial.
    return bool(a and b) and len(a & b) / len(a | b) >= 0.8


def _knowledge_db_urls(days: int) -> set[str]:
    """Return the URLs the wiki pipeline ingested in the last days days, or an empty set when postgres is unreachable."""
    sql = (f"select coalesce(json_agg(canonical_url), '[]') from knowledge.documents "
           f"where created_at >= now() - interval '{int(days)} day' and canonical_url is not null")
    try:
        out = subprocess.run(["docker", "exec", "-i", "postgres", "psql", "-U", "postgres", "-d", "kdan", "-At"],
                             input=sql, capture_output=True, text=True, check=True, timeout=60).stdout
        return {normalize_url(u) for u in json.loads(out.strip() or "[]")}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as e:
        print(f"candidates: knowledge DB URL lookup failed ({e!r}); cross-day dedup uses warroom.db only")
        return set()


async def _fetch_all():
    rss_module.RSS_FEEDS = {n: pipeline_config.RSS_FEEDS[n] for n in config.RSS_FEED_NAMES
                            if n in pipeline_config.RSS_FEEDS}
    items, errors = [], []
    try:
        items += await fetch_hackernews()
    except Exception as e:  # noqa: BLE001
        errors.append(f"HN: {e!r}")
    loop = asyncio.get_event_loop()
    jobs = [("RSS", lambda: rss_module.fetch_rss_feeds(hours=config.FRESH_HOURS)),
            ("Lobsters", fetch_lobsters), ("Google News", fetch_google_news)]
    results = await asyncio.gather(*[loop.run_in_executor(None, fn) for _, fn in jobs], return_exceptions=True)
    for (name, _), res in zip(jobs, results):
        if isinstance(res, Exception):
            errors.append(f"{name}: {res!r}")
        else:
            items += res
    return items, errors


def collect(date: str) -> tuple[list[dict], dict]:
    """Fetch every source and keep the fresh items not seen before.

    The kept items are also stored in warroom.db so the next days drop them.

    Returns:
        The candidates as dicts and the stats {fetched, errors, dropped, kept}.
    """
    init_db()
    raw, errors = asyncio.run(_fetch_all())
    stats = {"fetched": len(raw), "errors": errors}

    seen = {normalize_url(u) for u in get_recent_urls(date, days=config.CROSS_DAY_DAYS)}
    seen |= _knowledge_db_urls(config.CROSS_DAY_DAYS)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.FRESH_HOURS)

    out, keys, titles = [], set(), []
    dropped = {"same_day": 0, "seen_before": 0, "stale": 0, "similar_title": 0}
    for it in raw:
        key = normalize_url(it.url)
        if key in keys:
            dropped["same_day"] += 1
            continue
        if key in seen:
            dropped["seen_before"] += 1
            continue
        # Items without a date (HN, some feeds) count as new on the day they
        # are first seen; the cross-day check above drops them afterwards.
        if it.published_at and it.published_at < cutoff:
            dropped["stale"] += 1
            continue
        # Google News links are opaque redirects, so a repeat of a story we
        # already have only shows up as a near-identical title.
        tk = _title_key(it.title)
        if any(_similar(tk, t) for t in titles):
            dropped["similar_title"] += 1
            continue
        keys.add(key)
        titles.append(tk)
        out.append({
            "title": it.title.strip(),
            "url": it.url,
            "key": key,
            "source": it.source_name,
            "source_type": it.source_type.value,
            "published_at": it.published_at.isoformat() if it.published_at else None,
            "snippet": re.sub(r"\s+", " ", it.content or "")[: config.SNIPPET_CHARS],
            "score": it.score,
        })
    stats.update(dropped=dropped, kept=len(out))
    save_raw_items(date, [{"title": c["title"], "url": c["url"], "source": c["source"], "score": c["score"]} for c in out])
    return out, stats
