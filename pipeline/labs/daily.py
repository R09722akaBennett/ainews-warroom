"""Write the day's "今日前沿實驗室" brief from the labs' classified X posts.

Saved as periodic_summaries period labs_daily (start = end = date), which
export/labs.py publishes to the Labs page and labs.weekly compresses into the
Monday report. Re-running on the same day rewrites the brief from all posts
stored for that day.
"""

from __future__ import annotations

from rich.console import Console

from db.connection import get_conn
from db.summaries import save_summary
from labs.config import LABS
from labs.llm import call_llm
from prompts.labs_prompt import LABS_DAILY_PROMPT

console = Console()
NOTHING = "今天沒有重要動態。"


def _posts(date: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT company, title, url, published_at, category, content FROM competitor_items "
        "WHERE date = ? AND source LIKE 'X @%' AND ai_related = 1 AND category != 'pending' "
        "ORDER BY company, published_at", (date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_daily_brief(date: str) -> str | None:
    """Write and save the brief for date.

    Returns:
        The brief's markdown, or None when date has no classified X posts.

    Raises:
        labs.llm.LLMUnavailable: Gemini kept failing; nothing is saved.
    """
    posts = _posts(date)
    if not posts:
        console.print(f"[yellow]Labs daily: no classified X posts for {date}, skipping[/]")
        return None
    order = {k: i for i, k in enumerate(LABS)}
    posts.sort(key=lambda p: (order.get(p["company"], 99), p["published_at"] or ""))
    text = "\n\n".join(
        f"[{LABS.get(p['company'], {}).get('name', p['company'])}] {p['category']} | {p['published_at']} | {p['url']}\n"
        f"{p['content'] or p['title']}" for p in posts)
    content, usage = call_llm(LABS_DAILY_PROMPT.format(date=date, posts=text))
    content = content.strip()
    if content == NOTHING:
        console.print(f"[dim]Labs daily: {len(posts)} posts, nothing substantive[/]")
    labs = sorted({p["company"] for p in posts})
    save_summary("labs_daily", date, date, f"今日前沿實驗室 {date}", content,
                 tags={"labs": labs, "posts": len(posts)}, token_usage=usage)
    console.print(f"[green]Labs daily brief saved: {len(posts)} posts from {len(labs)} labs[/]")
    return content
