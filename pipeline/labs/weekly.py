"""Write the Monday labs weekly report from the past seven daily briefs."""

from __future__ import annotations

import json
from datetime import date as _date, timedelta

from rich.console import Console

from db.summaries import load_summaries, save_summary
from labs.daily import NOTHING
from labs.llm import call_llm
from prompts.labs_prompt import LABS_WEEKLY_FROM_DAILY_PROMPT

console = Console()


def _parse_json(text: str) -> dict:
    """Parse a JSON object from an LLM response, with or without a markdown fence."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def _describe(config: dict) -> str:
    """Return a lab's region and openness as the domain phrase the classifier prompt takes."""
    region = {"us": "US", "china": "China", "europe": "Europe"}.get(config.get("region"), "other region")
    openness = {"open": "open weights", "closed": "closed models", "mixed": "open and closed models"}.get(
        config.get("openness"), "")
    return ", ".join(x for x in (region, openness) if x)


def generate_weekly_from_daily(date: str) -> dict | None:
    """Compress the labs_daily briefs of the 7 days before date into a labs_weekly report.

    Returns:
        The saved {"title", "content"}, or None when no day in the window had
        a substantive brief. A response that is not a JSON object with a title
        and content is still saved: the raw text becomes the content under the
        default title, so a malformed answer does not lose the week.
    """
    end = _date.fromisoformat(date) - timedelta(days=1)
    start = end - timedelta(days=6)
    days = [d for d in load_summaries("labs_daily", str(start), str(end)) if d["content"].strip() != NOTHING]
    if not days:
        console.print(f"[yellow]Labs weekly: no daily briefs between {start} and {end}, skipping[/]")
        return None
    text = "\n\n---\n\n".join(f"### {d['start_date']}\n{d['content']}" for d in days)
    raw, usage = call_llm(LABS_WEEKLY_FROM_DAILY_PROMPT.format(start=start, end=end, days=text))
    try:
        parsed = _parse_json(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and parsed.get("title") and parsed.get("content"):
        report = {"title": parsed["title"], "content": parsed["content"]}
    else:
        console.print("[yellow]Labs weekly: response is not a JSON report, saving the raw text[/]")
        report = {"title": f"實驗室週報 ({start} ~ {end})", "content": raw.strip()}
    save_summary("labs_weekly", str(start), str(end), report["title"], report["content"],
                 tags={"days": len(days)}, token_usage=usage)
    console.print(f"[green]Labs weekly saved from {len(days)} daily briefs: {report['title']}[/]")
    return report
