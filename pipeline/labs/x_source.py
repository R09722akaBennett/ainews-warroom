"""Recent posts from the labs' X accounts, as extra lab news items.

Reads X_BEARER_TOKEN from the environment and does nothing without it. The X
API bills per post returned ($0.005) and per user looked up ($0.01), so every
call is bounded: handles are resolved to ids once and cached, each account is
read only past the newest post already seen (since_id), replies and reposts
are excluded, and X_DAILY_POST_CAP (default 150 posts per UTC day, about
$0.75) stops reading for the rest of the day. Accounts are read in LABS order,
tier 1 first, so the cap cuts tier 2 before tier 1.

State lives in pipeline/data/x_state.json (gitignored): user ids, since_ids
and the posts billed per UTC day.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from rich.console import Console

from labs.config import LABS

console = Console()

API = "https://api.x.com/2"
STATE = Path(__file__).resolve().parents[1] / "data" / "x_state.json"
FIRST_READ_HOURS = 24  # first read of an account: today only; later reads start from since_id
# One call returns up to 100 posts, so a busy launch day is read in full;
# X_DAILY_POST_CAP still bounds the total. The endpoint's minimum of 5 means
# the last call of a day can pass the cap by up to 4 posts.
PER_ACCOUNT_MAX = 100


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"users": {}, "since": {}, "billed": {}}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def _handles() -> list[tuple[str, str]]:
    return [(key, h) for key, cfg in LABS.items() for h in cfg.get("x_accounts", [])]


class _Stop(Exception):
    """X refused further reads for this run (rate limit, credits, auth)."""


def _get(client: httpx.Client, path: str, params: dict) -> dict:
    r = client.get(f"{API}{path}", params=params)
    if r.status_code in (401, 402, 403, 429):
        # Only the status and X's error title; never the request headers.
        title = ""
        try:
            title = r.json().get("title", "")
        except ValueError:
            pass
        raise _Stop(f"{r.status_code} {title}".strip())
    r.raise_for_status()
    return r.json()


def _resolve(client: httpx.Client, state: dict, handles: list[str]) -> None:
    todo = [h for h in handles if h.lower() not in state["users"]]
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        data = _get(client, "/users/by", {"usernames": ",".join(batch)})
        found = {u["username"].lower(): u["id"] for u in data.get("data", [])}
        for h in batch:
            # Unknown handles are cached as None so they are not paid for again.
            state["users"][h.lower()] = found.get(h.lower())
            if h.lower() not in found:
                console.print(f"    [yellow]X: @{h} not found, check labs/config.py[/]")


def _item(handle: str, post: dict) -> dict:
    text = (post.get("note_tweet") or {}).get("text") or post.get("text", "")
    first = text.strip().split("\n", 1)[0]
    return {
        "title": first if len(first) <= 140 else first[:137] + "...",
        "url": f"https://x.com/{handle}/status/{post['id']}",
        "source": f"X @{handle}",
        "published_at": post.get("created_at"),
        "content": text[:500],
    }


def fetch_x_items(client: httpx.Client | None = None) -> dict[str, list[dict]]:
    """Return {lab_key: [items]} of new posts; {} when X is not configured or refuses."""
    token = os.environ.get("X_BEARER_TOKEN")
    if not token and client is None:
        console.print("    [dim]X: X_BEARER_TOKEN not set, skipping[/]")
        return {}
    cap = int(os.environ.get("X_DAILY_POST_CAP", "150"))
    state = _load_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state["billed"] = {d: n for d, n in state.get("billed", {}).items() if d >= today}
    billed = state["billed"].get(today, 0)
    out: dict[str, list[dict]] = {}
    own = client is None
    client = client or httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=20)
    try:
        pairs = _handles()
        _resolve(client, state, [h for _, h in pairs])
        start = (datetime.now(timezone.utc) - timedelta(hours=FIRST_READ_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for key, handle in pairs:
            uid = state["users"].get(handle.lower())
            if not uid:
                continue
            if billed >= cap:
                console.print(f"    [yellow]X: daily cap {cap} reached, skipping the remaining accounts[/]")
                break
            params = {"max_results": max(5, min(PER_ACCOUNT_MAX, cap - billed)),
                      "exclude": "replies,retweets", "tweet.fields": "created_at,note_tweet"}
            if state["since"].get(uid):
                params["since_id"] = state["since"][uid]
            else:
                params["start_time"] = start
            data = _get(client, f"/users/{uid}/tweets", params)
            posts = data.get("data", [])
            billed += len(posts)
            if posts:
                state["since"][uid] = max(posts, key=lambda p: int(p["id"]))["id"]
                out.setdefault(key, []).extend(_item(handle, p) for p in posts)
    except _Stop as e:
        console.print(f"    [red]X: stopped for this run ({e})[/]")
    finally:
        state["billed"][today] = billed
        _save_state(state)
        if own:
            client.close()
    console.print(f"    X: {sum(len(v) for v in out.values())} posts, {billed}/{cap} billed today")
    return out
