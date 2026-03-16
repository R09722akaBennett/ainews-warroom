"""Competitor news classifier — batch LLM classification per company."""

from __future__ import annotations

import json
import os

import google.genai as genai
from rich.console import Console

from prompts.competitor_prompt import COMPETITOR_CLASSIFY_PROMPT

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON array from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def classify_batch(
    company_name: str,
    domain: str,
    items: list[dict],
) -> tuple[list[dict], dict | None]:
    """Classify a batch of items for one company.

    Returns (classified_items, token_usage).
    Each item gets added fields: ai_related, category, summary.
    """
    if not items:
        return [], None

    # Build numbered article list for prompt
    lines = []
    for i, item in enumerate(items):
        line = f"[{i}] {item['title']}"
        if item.get("content"):
            line += f"\n    {item['content'][:300]}"
        lines.append(line)
    articles_text = "\n\n".join(lines)

    prompt = COMPETITOR_CLASSIFY_PROMPT.format(
        company_name=company_name,
        domain=domain,
        articles_text=articles_text,
    )

    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    # Token usage
    token_usage = None
    um = getattr(response, "usage_metadata", None)
    if um:
        token_usage = {
            "input": getattr(um, "prompt_token_count", 0) or 0,
            "output": getattr(um, "candidates_token_count", 0) or 0,
            "total": getattr(um, "total_token_count", 0) or 0,
        }

    # Parse classification
    try:
        classifications = _parse_json_response(response.text)
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"    [red]Classification parse error: {e}[/]")
        # Fall back: mark all as ai_related with "other" category
        classifications = [
            {"index": i, "ai_related": True, "category": "other", "summary": item["title"]}
            for i, item in enumerate(items)
        ]

    # Merge classifications into items
    classified = []
    for i, item in enumerate(items):
        cls = next((c for c in classifications if c.get("index") == i), None)
        classified.append({
            **item,
            "ai_related": cls.get("ai_related", True) if cls else True,
            "category": cls.get("category", "other") if cls else "other",
            "summary": cls.get("summary", item["title"]) if cls else item["title"],
        })

    return classified, token_usage
