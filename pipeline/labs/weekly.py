"""Labs weekly report.

Since 2026-10-01 the Monday report compresses the past seven daily briefs
(generate_weekly_from_daily); generate_weekly_report is the older
per-item version, kept for reference.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

import google.genai as genai
from rich.console import Console

from db.connection import get_conn
from db.summaries import save_summary
from labs.config import LABS
from prompts.labs_prompt import COMPETITOR_WEEKLY_PROMPT

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

COMPANY_SUMMARY_PROMPT = """You track frontier AI labs for an ML engineer.
Summarize the following news about {company_name} ({domain}) from the past week.

Focus on:
- Model releases, benchmark results and research
- Products, APIs and pricing changes
- Compute, funding, acquisitions and partnerships
- People moving in or out, and policy or legal events

Write 3-5 bullet points in Traditional Chinese. Be concise and actionable.
If there's nothing significant, write "本週無重大動態".

**Important**: When referencing a specific article, use the ref-N tag from the article list (e.g. ref-0, ref-5).
Format: `相關文章的描述 (ref-0)` or `描述 (ref-0, ref-3)`

## Articles

{articles_text}
"""


def _call_llm(prompt: str) -> tuple[str, dict | None]:
    """Call Gemini and return (text, token_usage)."""
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    token_usage = None
    um = getattr(response, "usage_metadata", None)
    if um:
        token_usage = {
            "input": getattr(um, "prompt_token_count", 0) or 0,
            "output": getattr(um, "candidates_token_count", 0) or 0,
            "total": getattr(um, "total_token_count", 0) or 0,
        }
    return response.text, token_usage


def _parse_json(text: str) -> dict:
    """Parse JSON from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def _describe(config: dict) -> str:
    region = {"us": "US", "china": "China", "europe": "Europe"}.get(config.get("region"), "other region")
    openness = {"open": "open weights", "closed": "closed models", "mixed": "open and closed models"}.get(
        config.get("openness"), "")
    return ", ".join(x for x in (region, openness) if x)


def generate_weekly_report(date: str) -> dict | None:
    """Generate the competitor weekly report.

    Step 1: Per-company summary (1 LLM call each, only for companies with items)
    Step 2: Combined weekly report (1 LLM call)

    Returns token_usage totals.
    """
    start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    # Get classified AI-related items from the past week
    conn = get_conn()
    rows = conn.execute(
        "SELECT company, title, url, source, category, summary "
        "FROM competitor_items "
        "WHERE date >= ? AND date <= ? AND ai_related = 1 AND category != 'pending' "
        "ORDER BY company, date DESC",
        (start, date),
    ).fetchall()
    conn.close()

    if not rows:
        console.print("  [yellow]No classified competitor items found. Skipping weekly report.[/]")
        return None

    # Group by company
    by_company: dict[str, list[dict]] = {}
    for r in rows:
        by_company.setdefault(r["company"], []).append(dict(r))

    total_tokens = {"input": 0, "output": 0, "total": 0}

    # Build a global ref index across all companies
    all_ref_items: list[dict] = []
    for company_key in sorted(by_company.keys()):
        for it in by_company[company_key]:
            it["_ref_idx"] = len(all_ref_items)
            all_ref_items.append({
                "url": it.get("url", ""),
                "title": it.get("title", ""),
                "company": company_key,
            })

    # Step 1: Per-company summaries for tier 1; tier 2 labs are listed as-is
    # and summarized only inside the combined report.
    company_summaries: dict[str, str] = {}
    for company_key, items in by_company.items():
        config = LABS.get(company_key, {})
        if config.get("tier", 1) != 1:
            company_summaries[company_key] = "\n".join(
                f"- [ref-{it['_ref_idx']}] [{it['category']}] {it['title']}" for it in items)
            continue
        name = config.get("name", company_key)
        domain = _describe(config)

        console.print(f"  Summarizing [cyan]{name}[/] ({len(items)} items)...", end=" ")

        articles_text = "\n".join(
            f"- [ref-{it['_ref_idx']}] [{it['category']}] {it['title']}"
            + (f"\n  {it['summary']}" if it.get("summary") else "")
            for it in items
        )

        prompt = COMPANY_SUMMARY_PROMPT.format(
            company_name=name,
            domain=domain,
            articles_text=articles_text,
        )

        text, token_usage = _call_llm(prompt)
        if token_usage:
            for k in total_tokens:
                total_tokens[k] += token_usage.get(k, 0)

        company_summaries[company_key] = text.strip()
        console.print("[green]done[/]")

    # Step 2: Combined weekly report
    console.print("  Generating [bold]combined weekly report[/]...", end=" ")

    news_parts = []
    for company_key, summary_text in company_summaries.items():
        config = LABS.get(company_key, {})
        name = config.get("name", company_key)
        domain = _describe(config)
        item_count = len(by_company.get(company_key, []))
        tier = config.get("tier", 1)
        news_parts.append(f"### [Tier {tier}] {name} ({domain}) — {item_count} items\n{summary_text}")

    news_text = "\n\n---\n\n".join(news_parts)

    prompt = COMPETITOR_WEEKLY_PROMPT.format(news_text=news_text)
    text, token_usage = _call_llm(prompt)
    if token_usage:
        for k in total_tokens:
            total_tokens[k] += token_usage.get(k, 0)

    console.print("[green]done[/]")

    # Parse the report
    try:
        result = _parse_json(text)
        title = result.get("title", f"實驗室週報 ({start} ~ {date})")
        content = result.get("content", text)
        tags = result.get("tags") or {}
    except (json.JSONDecodeError, KeyError):
        title = f"實驗室週報 ({start} ~ {date})"
        content = text
        tags = {}

    # Store ref items mapping for website ref linking
    tags["refItems"] = all_ref_items

    # Save to periodic_summaries
    save_summary(
        "labs_weekly", start, date,
        title, content, tags, total_tokens,
    )

    console.print(f"  [green]✓[/] Saved: {title}")
    console.print(f"  Tokens: input={total_tokens['input']:,} output={total_tokens['output']:,} total={total_tokens['total']:,}")

    return total_tokens


def generate_weekly_from_daily(date: str) -> dict | None:
    """Compress the labs_daily briefs of the 7 days before date into a labs_weekly report."""
    from datetime import date as _date

    from db.summaries import load_summaries
    from prompts.labs_prompt import LABS_WEEKLY_FROM_DAILY_PROMPT

    end = _date.fromisoformat(date) - timedelta(days=1)
    start = end - timedelta(days=6)
    days = [d for d in load_summaries("labs_daily", str(start), str(end)) if d["content"].strip() != "今天沒有重要動態。"]
    if not days:
        console.print(f"[yellow]Labs weekly: no daily briefs between {start} and {end}, skipping[/]")
        return None
    text = "\n\n---\n\n".join(f"### {d['start_date']}\n{d['content']}" for d in days)
    raw, usage = _call_llm(LABS_WEEKLY_FROM_DAILY_PROMPT.format(start=start, end=end, days=text))
    report = _parse_json(raw)
    save_summary("labs_weekly", str(start), str(end), report["title"], report["content"],
                 tags={"days": len(days)}, token_usage=usage)
    console.print(f"[green]Labs weekly saved from {len(days)} daily briefs: {report['title']}[/]")
    return report
