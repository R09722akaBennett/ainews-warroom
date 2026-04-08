"""Workflow runner — deterministic pipeline for daily report generation.

Flow:
  1. Collect news from all sources (deterministic)
  2. Load context: recent digests + company info (deterministic)
  3. Build prompt and call LLM once to generate report
  4. Parse response and save to DB + markdown file (deterministic)
"""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

import google.genai as genai
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console


class Topic(BaseModel):
    topic: str
    headline: str
    summary: str
    url: str = ""
    source: str = ""


class Tags(BaseModel):
    companies: list[str]
    models: list[str]
    topics: list[str]


class Report(BaseModel):
    title: str
    topics: list[Topic]
    tags: Tags
    markdown: str

from db import init_db, save_digest
from config import OUTPUT_DIR
from models import NewsItem
from prompts import REPORT_SYSTEM_PROMPT
from agent.collector import collect_news
from agent.context import load_recent_digests, load_company_context
from agent.ref_fixer import fix_refs

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _build_user_prompt(
    date: str,
    items: list[NewsItem],
    recent_digests: list,
    company_context: str,
) -> str:
    """Build the user prompt with all collected data."""
    parts = [f"今天是 {date}。請根據以下資料產出今日 AI 戰情報告。\n"]

    # Today's news — grouped by date (newest first), shuffled within each day
    by_date: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        date_key = item.published_at.strftime("%Y-%m-%d") if item.published_at else "0000-00-00"
        by_date[date_key].append(item)
    sorted_items: list[NewsItem] = []
    for dk in sorted(by_date.keys(), reverse=True):
        group = by_date[dk]
        random.shuffle(group)
        sorted_items.extend(group)
    parts.append("## 今日收集的 AI 新聞（按發佈日期排序，最新在前）\n")
    for i, item in enumerate(sorted_items):
        date_str = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else ""
        line = f"[{i}] [{item.source_name}] {item.title}"
        if date_str:
            line += f"\n    Published: {date_str}"
        if item.url:
            line += f"\n    URL: {item.url}"
        if item.content:
            line += f"\n    {item.content}"
        parts.append(line)
    parts.append("")

    # Recent digests (7 days)
    if recent_digests:
        parts.append("## 過去 7 天的報告摘要（用於延續性分析）\n")
        for d in recent_digests:
            insights_preview = d.insights if d.insights else "(無)"
            parts.append(f"### {d.date} — {d.title}\n{insights_preview}\n")
        parts.append("")

    # Company context
    if company_context:
        parts.append(f"## KDAN Mobile 公司資訊\n\n{company_context}\n")

    return "\n".join(parts)


def _parse_report_response(text: str) -> dict:
    """Parse the LLM JSON response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def _write_markdown(date: str, content: str, dry_run: bool) -> str:
    """Write markdown report to pipeline/output/."""
    if dry_run:
        console.print("\n[yellow]--- DRY RUN ---[/]")
        console.print(content[:3000])
        if len(content) > 3000:
            console.print(f"\n[dim]... ({len(content) - 3000} more chars)[/]")
        return "(dry-run)"

    dt = datetime.strptime(date, "%Y-%m-%d")
    filename = f"{dt.strftime('%y-%m-%d')}-ai-warroom.md"
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


async def run_daily(date: str, dry_run: bool = False):
    """Execute the daily warroom pipeline."""
    init_db()

    console.print(f"\n[bold]KDAN AI War Room — {date}[/]\n")

    # Step 1: Collect news (deterministic)
    console.print("[bold]Step 1/4:[/] Collecting news...")
    items, raw_count = await collect_news(date)

    # Step 2: Load context (deterministic)
    console.print("[bold]Step 2/4:[/] Loading context...")
    recent_digests = load_recent_digests(days=7)
    company_context = load_company_context()

    # Step 3: Generate report (one LLM call)
    console.print("[bold]Step 3/4:[/] Generating report...")
    user_prompt = _build_user_prompt(date, items, recent_digests, company_context)

    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {"role": "user", "parts": [{"text": REPORT_SYSTEM_PROMPT + "\n\n" + user_prompt}]},
        ],
        config={
            "response_mime_type": "application/json",
            "response_json_schema": Report.model_json_schema(),
        },
    )

    # Extract token usage
    token_usage = None
    um = getattr(response, "usage_metadata", None)
    if um:
        token_usage = {
            "input": getattr(um, "prompt_token_count", 0) or 0,
            "output": getattr(um, "candidates_token_count", 0) or 0,
            "total": getattr(um, "total_token_count", 0) or 0,
        }

    report = Report.model_validate_json(response.text)
    title = report.title or f"KDAN AI 戰情報告 ({date})"
    topics = [t.model_dump() for t in report.topics]
    tags = report.tags.model_dump()
    markdown = report.markdown

    console.print(f"  [green]✓[/] Report generated: {title}")
    console.print(f"  [green]✓[/] Topics: {len(topics)}, Tags: {tags.keys() if tags else 'none'}")
    if token_usage:
        console.print(f"  [green]✓[/] Tokens: input={token_usage['input']:,} output={token_usage['output']:,} total={token_usage['total']:,}")

    # Fix hallucinated ref-N numbers
    markdown = fix_refs(markdown, items)

    # Step 4: Save (deterministic)
    console.print("[bold]Step 4/4:[/] Saving...")

    # Save to DB
    news_items = [{"title": it.title, "url": it.url, "source": it.source_name} for it in items]
    save_digest(date, title, news_items, markdown, raw_count, topics, tags, token_usage)
    console.print(f"  [green]✓[/] Saved to DB")

    # Write markdown file
    filepath = _write_markdown(date, markdown, dry_run)
    console.print(f"  [green]✓[/] Markdown: {filepath}")

    console.print(f"\n[bold green]Done.[/]")
    return markdown


async def main():
    parser = argparse.ArgumentParser(description="KDAN AI War Room — Daily Report")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--date", type=str, default=None, help="Override date (YYYY-MM-DD)")
    args = parser.parse_args()

    load_dotenv()
    today = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await run_daily(today, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
