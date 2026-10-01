"""Recent posts from the labs' X accounts, as extra lab news items.

Reads X_BEARER_TOKEN from the environment and does nothing without it. The X
API bills per post returned ($0.005) and per user looked up ($0.01), so every
call is bounded: handles are resolved to ids once and cached, each account is
read only past the newest post already seen (since_id) and paged until done,
reposts are excluded, and X_DAILY_POST_CAP (default 300 posts per UTC day,
about $1.50) stops reading for the rest of the day. The cap is checked only
between accounts, so an account is always read in full; the accounts it
skips are read in full on the next run from their since_id. Accounts are read
in LABS order, tier 1 first, so the cap delays tier 2 before tier 1.

Replies are requested because a lab's thread continues as replies to itself;
those parts are merged into the thread's first post, and replies to other
accounts are dropped. X bills the dropped replies too, so the state records
both the posts billed and the posts kept per UTC day for the cost review.

State lives in pipeline/data/x_state.json (gitignored): user ids, since_ids
and per-day counts of posts billed, posts kept and users looked up for the
last 90 days, which export/costs.py prices. Deduplication is by time: post ids are
snowflakes that grow with the posting time, so reading past since_id returns
exactly the posts published after the last read; the labs table dedupes the
post URLs once more.

Posts are kept in full: long posts come from note_tweet, and t.co links are
replaced by their expanded URLs.
"""

from __future__ import annotations

import html
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
PAGE_SIZE = 100  # the endpoint's maximum per page
PRICE_PER_POST = 0.005
HISTORY_DAYS = 90
FIELDS = "created_at,note_tweet,entities,conversation_id,in_reply_to_user_id"


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"users": {}, "since": {}, "billed": {}, "kept": {}, "lookups": {}}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def _handles() -> list[tuple[str, str]]:
    return [(key, h) for key, cfg in LABS.items() for h in cfg.get("x_accounts", [])]


class _Stop(Exception):
    """X refused further reads for this run (rate limit, credits, auth)."""


# Any of these ends the run's reads the same way: the posts already read are
# returned and saved, and the accounts not read wait for the next run.
_STOP_ERRORS = (_Stop, httpx.HTTPError)


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


def _resolve(client: httpx.Client, state: dict, handles: list[str], today: str) -> None:
    """Cache the user ids of handles not looked up yet, counting the billed lookups under today."""
    todo = [h for h in handles if h.lower() not in state["users"]]
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        data = _get(client, "/users/by", {"usernames": ",".join(batch)})
        found = {u["username"].lower(): u["id"] for u in data.get("data", [])}
        # X bills each user it returns; handles it does not find cost nothing.
        state["lookups"][today] = state["lookups"].get(today, 0) + len(found)
        for h in batch:
            # Unknown handles are cached as None so they are not paid for again.
            state["users"][h.lower()] = found.get(h.lower())
            if h.lower() not in found:
                console.print(f"    [yellow]X: @{h} not found, check labs/config.py[/]")


def _full_text(post: dict) -> str:
    """Return the post's complete text with t.co links expanded."""
    long = post.get("note_tweet") or {}
    text = long.get("text") or post.get("text", "")
    for u in ((long.get("entities") or {}).get("urls") or []) + ((post.get("entities") or {}).get("urls") or []):
        if u.get("url") and u.get("expanded_url"):
            text = text.replace(u["url"], u["expanded_url"])
    # X returns post text HTML-escaped ("&amp;", "&lt;"), which showed up as-is on the site.
    return html.unescape(text).strip()


def _item(handle: str, post: dict) -> dict:
    text = "\n\n".join(_full_text(p) for p in [post, *post.get("thread", [])])
    first = text.split("\n", 1)[0]
    return {
        "title": first if len(first) <= 140 else first[:137] + "...",
        "url": f"https://x.com/{handle}/status/{post['id']}",
        "source": f"X @{handle}",
        "published_at": post.get("created_at"),
        "content": text,
        "handle": handle,
        "raw": post,  # the X API object as returned, stored in knowledge DB
    }


def _read_account(client: httpx.Client, uid: str, since: str | None, start: str, posts: list[dict]) -> None:
    """Append every post of one account newer than since (or since start) to posts.

    Posts are appended page by page as X returns them, so when a later page
    fails the caller still sees, and bills, the pages already returned.
    """
    params = {"max_results": PAGE_SIZE, "exclude": "retweets", "tweet.fields": FIELDS}
    if since:
        params["since_id"] = since
    else:
        params["start_time"] = start
    while True:
        data = _get(client, f"/users/{uid}/tweets", params)
        posts.extend(data.get("data", []))
        token = (data.get("meta") or {}).get("next_token")
        if not token:
            break
        params["pagination_token"] = token


def _threads(uid: str, posts: list[dict]) -> list[dict]:
    """Return the account's own posts with self-reply thread parts merged into their first post.

    A part whose first post came in an earlier run stays a post of its own.
    Replies to other accounts are dropped.
    """
    own = [p for p in posts if not p.get("in_reply_to_user_id") or p["in_reply_to_user_id"] == uid]
    roots = {p["id"]: p for p in own if p.get("conversation_id", p["id"]) == p["id"]}
    out, parts = [], {}
    for p in own:
        conv = p.get("conversation_id", p["id"])
        if p["id"] != conv and conv in roots:
            parts.setdefault(conv, []).append(p)
        else:
            out.append(p)
    for p in out:
        if p["id"] in parts:
            p["thread"] = parts[p["id"]]
    return out


def fetch_x_items(client: httpx.Client | None = None) -> dict[str, list[dict]]:
    """Read the labs' new posts.

    Returns:
        {lab_key: [items]} of the accounts read in full this run; {} when X is
        not configured. When X refuses or fails part-way (4xx refusal, 5xx,
        timeout), reading stops and the accounts already read are returned;
        the failed account keeps its since_id and is read again next run.
    """
    token = os.environ.get("X_BEARER_TOKEN")
    if not token and client is None:
        console.print("    [dim]X: X_BEARER_TOKEN not set, skipping[/]")
        return {}
    cap = int(os.environ.get("X_DAILY_POST_CAP", "300"))
    state = _load_state()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    oldest = (now - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    for k in ("billed", "kept", "lookups"):
        state[k] = {d: n for d, n in state.get(k, {}).items() if d >= oldest}
    billed, kept = state["billed"].get(today, 0), state["kept"].get(today, 0)
    out: dict[str, list[dict]] = {}
    own = client is None
    client = client or httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=20)
    try:
        pairs = _handles()
        _resolve(client, state, [h for _, h in pairs], today)
        start = (now - timedelta(hours=FIRST_READ_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for key, handle in pairs:
            uid = state["users"].get(handle.lower())
            if not uid:
                continue
            if billed >= cap:
                console.print(f"    [yellow]X: daily cap {cap} reached, the remaining accounts wait for the next run[/]")
                break
            posts: list[dict] = []
            try:
                _read_account(client, uid, state["since"].get(uid), start, posts)
            finally:
                billed += len(posts)
            posts.sort(key=lambda p: int(p["id"]))
            if posts:
                # Only after the account was read to the end, so a refused page
                # leaves since_id where it was and the next run reads it again.
                state["since"][uid] = posts[-1]["id"]
                items = [_item(handle, p) for p in _threads(uid, posts)]
                kept += len(items)
                out.setdefault(key, []).extend(items)
    except _STOP_ERRORS as e:
        # The status alone: the request URL repeats every query parameter.
        detail = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else e
        console.print(f"    [red]X: stopped for this run ({type(e).__name__}: {detail})[/]")
    finally:
        state["billed"][today], state["kept"][today] = billed, kept
        _save_state(state)
        if own:
            client.close()
    console.print(f"    X: {sum(len(v) for v in out.values())} posts this run; today {billed} billed "
                  f"(${billed * PRICE_PER_POST:.2f}), {kept} kept, {state['lookups'].get(today, 0)} user lookups, "
                  f"cap {cap}")
    return out
