"""Collect Latent Space podcast episodes for the site's Podcasts page.

For each podcast post since SITE_SINCE that is not yet in data/podcasts/:
fetch the full post (substack.com posts/by-id with the subscriber cookie;
the custom domain www.latent.space ignores it), parse it, store it in
knowledge DB as podcast:latent_space (one section per transcript chapter,
the parsed episode kept in the raw payload), and write a structured Chinese
summary with Gemini. Each episode is cached as data/podcasts/<slug>.json, so
an episode is fetched and summarised once; --force redoes one slug.

Substack also mails every post in full to the subscriber, so when the
cookie has expired or the API answer has no transcript, the post is read
from that mail instead (Gmail IMAP, read-only; the mail is matched by title).
Some posts (the 🔬 science series) publish show notes
but no transcript; those are summarised from the notes and exported with an
empty transcript and no quotes. Quotes the model returns are kept only when
they occur verbatim in the transcript, so a paraphrase never shows up inside
quotation marks.

When Gemini's answer cannot be parsed, <slug>.failed in the cache records the
error and the attempt count; after MAX_SUMMARY_ATTEMPTS the slug is skipped
so one bad episode does not cost a Gemini call every day. --force retries it.

Usage:
    cd pipeline
    uv run --no-sync python -m podcasts            # dry-run: list what would be collected
    uv run --no-sync python -m podcasts --live     # fetch, store, summarise
    uv run --no-sync python -m podcasts --live --force devday-2026
"""

from __future__ import annotations

import argparse
import email
import email.header
import email.message
import imaplib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google import genai

from podcasts.parse import parse_episode
from prompts.podcast_prompt import PODCAST_PROMPT

SITE = "https://www.latent.space"
SITE_SINCE = "2026-09-01"
CACHE = Path(__file__).resolve().parents[1] / "data" / "podcasts"
API = os.getenv("KNOWLEDGE_API", "http://127.0.0.1:8000")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Substack's API answers 403 to Python's default User-Agent;
# a browser UA for the custom domain and curl's for substack.com both work.
UA_SITE = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
UA_API = "curl/8.5.0"
TRANSCRIPT_CHARS = 400_000  # a 141-minute episode is about 160k characters
MAIL_SENDER = "swyx@substack.com"  # AINews issues and receipts come from the same address
MAX_SUMMARY_ATTEMPTS = 3
_client = None


class SummaryParseError(ValueError):
    """Gemini's answer for an episode was not the JSON the prompt asks for."""


def _gemini():
    # One client for the run: a client created inline is garbage-collected
    # while its request is still open ("client has been closed").
    global _client
    _client = _client or genai.Client()
    return _client


def _get_json(url: str, ua: str, cookie: str | None = None):
    headers = {"User-Agent": ua, **({"Cookie": f"substack.sid={cookie}"} if cookie else {})}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return json.load(r)


def list_episodes() -> list[dict]:
    """Return podcast posts since SITE_SINCE from the archive, newest first."""
    out, offset = [], 0
    while True:
        page = _get_json(f"{SITE}/api/v1/archive?sort=new&offset={offset}&limit=25", UA_SITE)
        if not page:
            break
        out += [p for p in page if p.get("type") == "podcast" and p["post_date"][:10] >= SITE_SINCE]
        if page[-1]["post_date"][:10] < SITE_SINCE:
            break
        offset += 25
    return out


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower().replace("’", "'")).strip()


def _failed_path(slug: str) -> Path:
    return CACHE / f"{slug}.failed"


def _failed_attempts(slug: str) -> int:
    try:
        return int(json.loads(_failed_path(slug).read_text(encoding="utf-8")).get("attempts", 0))
    except (OSError, ValueError):
        return 0


def _record_failure(slug: str, error: Exception) -> int:
    """Count one more failed summary for slug in its .failed file; return the new count."""
    attempts = _failed_attempts(slug) + 1
    _failed_path(slug).write_text(json.dumps({
        "attempts": attempts, "error": f"{type(error).__name__}: {str(error)[:300]}",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, ensure_ascii=False), encoding="utf-8")
    return attempts


def summarise(ep: dict) -> tuple[dict, dict | None]:
    """Write the episode's structured Chinese summary with Gemini.

    Returns:
        The summary dict, with quotes kept only when they occur verbatim in
        the transcript, and the token usage (None without usage metadata).

    Raises:
        SummaryParseError: The answer was empty or not a JSON object.
    """
    turns = "\n".join(f"{t['speaker']} [{t['t']}]: {t['text']}" for c in ep["transcript"] for t in c["turns"])
    prompt = PODCAST_PROMPT.format(
        title=ep["title"], subtitle=ep.get("subtitle") or "", intro="\n".join(ep["intro"]),
        we_discuss="\n".join(f"- {x}" for x in ep["we_discuss"]) or "（無）",
        guests="\n".join(f"- {g['name']}：{g['role']}" for g in ep["guests"]) or "（無）",
        chapters="\n".join(f"{c['t']} {c['title']}" for c in ep["chapters"]) or "（無）",
        transcript=turns[:TRANSCRIPT_CHARS] or "（原文沒有逐字稿，只根據上面的編者介紹整理；quotes 回傳空陣列）")
    resp = _gemini().models.generate_content(
        model=GEMINI_MODEL, contents=prompt, config={"response_mime_type": "application/json"})
    try:
        data = json.loads(resp.text)
    except (TypeError, ValueError) as e:  # TypeError: text is None (blocked answer)
        raise SummaryParseError(f"unparseable summary: {e}") from e
    if not isinstance(data, dict):
        raise SummaryParseError(f"summary is a {type(data).__name__}, not an object")
    body = _norm(turns)
    # Without a transcript the show notes are the editor's words, not the guests'.
    data["quotes"] = [q for q in data.get("quotes", []) if q.get("en") and body and _norm(q["en"]) in body]
    um = getattr(resp, "usage_metadata", None)
    usage = {"input": um.prompt_token_count or 0, "output": um.candidates_token_count or 0,
             "total": um.total_token_count or 0} if um else None
    return data, usage


def ingest(ep: dict) -> str:
    """Store the episode in knowledge DB; return the status, or "failed: ..." without raising."""
    token = os.getenv("INGEST_API_TOKEN")
    if not token:
        return "skipped: INGEST_API_TOKEN not set"
    sections = [{"title": c["title"], "category": "podcast-transcript",
                 "text": "\n\n".join(f"{t['speaker']} [{t['t']}]: {t['text']}" for t in c["turns"])}
                for c in ep["transcript"]]
    if ep["intro"]:
        sections.insert(0, {"title": "Episode notes", "category": "podcast-notes", "text": "\n\n".join(ep["intro"])})
    msg = {"id": f"latent-space-{ep['slug']}", "title": ep["title"], "url": ep["url"], "author": "Latent Space",
           "published_at": ep["date"], "sections": sections, "episode": {k: v for k, v in ep.items() if k != "summary"}}
    req = urllib.request.Request(f"{API}/ingest/email", method="POST",
                                 data=json.dumps({"source_key": "podcast:latent_space", "message": msg}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r).get("status", "ok")
    except Exception as e:  # noqa: BLE001
        return f"failed: {type(e).__name__}"


def _usable(ep: dict) -> bool:
    return bool(ep["transcript"]) or len(" ".join(ep["intro"]).split()) >= 300


def _mail_html(msg: email.message.Message) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def episode_from_mail(post: dict) -> dict | None:
    """Return the post parsed from its subscriber mail, or None when no such mail is found.

    The mailbox is opened read-only, so nothing is marked as read. The mail is
    matched by title because the sender also mails AINews issues, receipts and
    verification codes. Returns None when the IMAP credentials are missing.
    """
    user, password = os.getenv("GMAIL_IMAP_USER"), os.getenv("GMAIL_IMAP_PASSWORD")
    if not user or not password:
        return None
    since = (datetime.fromisoformat(post["post_date"][:10]) - timedelta(days=1)).strftime("%d-%b-%Y")
    want = _norm(post["title"])
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        imap.login(user, password)
        imap.select('"[Gmail]/All Mail"', readonly=True)
        _, data = imap.search(None, f'(FROM "{MAIL_SENDER}" SINCE {since})')
        for num in data[0].split():
            _, raw = imap.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(raw[0][1])
            subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
            if _norm(subject) == want:
                return parse_episode(_mail_html(msg))
    finally:
        imap.logout()
    return None


def collect(post: dict) -> dict:
    """Fetch and parse one post in full; raise ValueError when it has neither transcript nor notes.

    The web post comes through Substack's API with the subscriber cookie. When
    the cookie is missing or rejected, or the answer carries no transcript,
    the subscriber mail of the same post is read instead, so an expired cookie
    does not stop collection. "fetchedFrom" records which one was used.
    """
    sid = os.getenv("SUBSTACK_SID")
    ep, source, problem = None, "api", None
    if not sid:
        problem = "SUBSTACK_SID not set"
    else:
        try:
            full = _get_json(f"https://substack.com/api/v1/posts/by-id/{post['id']}", UA_API, sid)
            full = full.get("post") or full
            ep = parse_episode(full.get("body_html") or "")
            if not _usable(ep):
                problem = "neither a transcript nor show notes in the API post"
        except urllib.error.HTTPError as e:
            if e.code not in (401, 403):
                raise
            problem = f"API answered {e.code} (SUBSTACK_SID expired?)"
    if problem:
        from_mail = episode_from_mail(post)
        if from_mail and _usable(from_mail):
            print(f"podcasts: {post['slug']}: {problem}; using the subscriber mail")
            ep, source = from_mail, "mail"
        elif ep is None:
            raise ValueError(f"{problem}; no subscriber mail for this post either")
        else:
            raise ValueError(f"{problem} (paywalled or a new post layout); no usable subscriber mail either")
    ep.update({
        "fetchedFrom": source,
        "slug": post["slug"], "title": post["title"], "subtitle": post.get("subtitle") or "",
        "date": post["post_date"][:10], "url": post.get("canonical_url") or f"{SITE}/p/{post['slug']}",
        "duration": int(post.get("podcast_duration") or 0), "show": "Latent Space",
        "image": post.get("podcast_episode_image_url") or post.get("cover_image"),
    })
    return ep


def main() -> int:
    ap = argparse.ArgumentParser(description="收集 Latent Space podcast：全文、逐字稿、中文結構化摘要")
    ap.add_argument("--live", action="store_true", help="真的抓取、寫入 knowledge DB 並呼叫 Gemini（預設只列出）")
    ap.add_argument("--force", metavar="SLUG", help="重做這一集（重新抓取與摘要）")
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    posts = list_episodes()
    todo = [p for p in posts if not (CACHE / f"{p['slug']}.json").exists() or p["slug"] == args.force]
    given_up = [p for p in todo if p["slug"] != args.force and _failed_attempts(p["slug"]) >= MAX_SUMMARY_ATTEMPTS]
    todo = [p for p in todo if p not in given_up]
    for p in given_up:
        print(f"podcasts: {p['slug']} skipped after {MAX_SUMMARY_ATTEMPTS} unparseable summaries "
              f"(see {p['slug']}.failed; --force {p['slug']} retries)")
    if not args.live:
        for p in todo:
            print(f"[dry-run] Will collect {p['post_date'][:10]} {p['slug']} — {p['title'][:70]}")
        print(f"[dry-run] {len(todo)} of {len(posts)} episodes since {SITE_SINCE} are new")
        return 0
    failed = 0
    for p in todo:
        try:
            ep = collect(p)
            try:
                ep["summary"], ep["tokenUsage"] = summarise(ep)
            except SummaryParseError as e:
                attempts = _record_failure(p["slug"], e)
                failed += 1
                print(f"podcasts: {p['slug']} failed ({e}); attempt {attempts} of {MAX_SUMMARY_ATTEMPTS}")
                continue
            ep["knowledge"] = ingest(ep)
            ep["collectedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            (CACHE / f"{p['slug']}.json").write_text(json.dumps(ep, ensure_ascii=False, indent=1), encoding="utf-8")
            _failed_path(p["slug"]).unlink(missing_ok=True)
            turns = sum(len(c["turns"]) for c in ep["transcript"])
            print(f"podcasts: {p['slug']} ok ({len(ep['transcript'])} chapters, {turns} turns, "
                  f"{len(ep['summary'].get('quotes', []))} quotes, knowledge {ep['knowledge']}, "
                  f"from {ep['fetchedFrom']})")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"podcasts: {p['slug']} failed ({type(e).__name__}: {str(e)[:160]})")
    print(f"podcasts: {len(todo) - failed} collected, {failed} failed, {len(posts)} episodes since {SITE_SINCE}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
