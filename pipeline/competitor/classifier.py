"""Competitor news classifier — batch LLM classification per company."""

from __future__ import annotations

import json
import os
import time

import google.genai as genai
import httpx
from rich.console import Console

from prompts.competitor_prompt import COMPETITOR_CLASSIFY_PROMPT

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
BATCH_SIZE = 30  # Max items per LLM call to avoid truncated responses
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Transient errors worth retrying
_RETRYABLE = (httpx.RemoteProtocolError, httpx.ReadTimeout, ConnectionError)


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON array from LLM response, handling markdown fences and truncation."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # Try normal parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: parse individual objects from truncated JSON array
    # Handles cases like "[{...},{...},{..." where the array is cut off
    decoder = json.JSONDecoder()
    results = []
    # Skip leading '['
    pos = text.find("[")
    if pos == -1:
        raise json.JSONDecodeError("No JSON array found", text, 0)
    pos += 1

    while pos < len(text):
        # Skip whitespace and commas
        while pos < len(text) and text[pos] in " ,\n\r\t":
            pos += 1
        if pos >= len(text) or text[pos] == "]":
            break
        try:
            obj, end_pos = decoder.raw_decode(text, pos)
            results.append(obj)
            pos = end_pos
        except json.JSONDecodeError:
            break  # Can't parse more — return what we have

    if not results:
        raise json.JSONDecodeError("No valid JSON objects found", text, 0)
    return results


def _call_llm(prompt: str) -> tuple[str, dict | None]:
    """Call Gemini with retry logic for transient errors."""
    client = genai.Client()
    last_exc = None

    for attempt in range(MAX_RETRIES):
        try:
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
        except _RETRYABLE as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                console.print(f"    [yellow]Retry {attempt + 1}/{MAX_RETRIES} after {delay}s ({type(e).__name__})[/]")
                time.sleep(delay)

    raise last_exc  # type: ignore[misc]


def _classify_chunk(
    company_name: str,
    domain: str,
    items: list[dict],
    index_offset: int,
) -> tuple[list[dict], dict | None]:
    """Classify a single chunk of items."""
    lines = []
    for i, item in enumerate(items):
        idx = index_offset + i
        line = f"[{idx}] {item['title']}"
        if item.get("content"):
            line += f"\n    {item['content'][:300]}"
        lines.append(line)
    articles_text = "\n\n".join(lines)

    prompt = COMPETITOR_CLASSIFY_PROMPT.format(
        company_name=company_name,
        domain=domain,
        articles_text=articles_text,
    )

    text, token_usage = _call_llm(prompt)

    try:
        classifications = _parse_json_response(text)
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"    [red]Classification parse error: {e}[/]")
        classifications = [
            {"index": index_offset + i, "ai_related": True, "category": "other", "summary": item["title"]}
            for i, item in enumerate(items)
        ]

    return classifications, token_usage


def classify_batch(
    company_name: str,
    domain: str,
    items: list[dict],
) -> tuple[list[dict], dict | None]:
    """Classify a batch of items for one company.

    Returns (classified_items, token_usage).
    Each item gets added fields: ai_related, category, summary.
    Items are split into chunks of BATCH_SIZE to avoid truncated LLM responses.
    """
    if not items:
        return [], None

    # Split into chunks
    all_classifications: list[dict] = []
    total_usage: dict | None = None

    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start : start + BATCH_SIZE]
        if len(items) > BATCH_SIZE:
            console.print(f"    [dim]chunk {start // BATCH_SIZE + 1} ({start}–{start + len(chunk) - 1})[/]")

        classifications, token_usage = _classify_chunk(company_name, domain, chunk, start)
        all_classifications.extend(classifications)

        # Aggregate token usage
        if token_usage:
            if total_usage is None:
                total_usage = {"input": 0, "output": 0, "total": 0}
            for k in ("input", "output", "total"):
                total_usage[k] += token_usage[k]

    # Merge classifications into items
    classified = []
    for i, item in enumerate(items):
        cls = next((c for c in all_classifications if c.get("index") == i), None)
        classified.append({
            **item,
            "ai_related": cls.get("ai_related", True) if cls else True,
            "category": cls.get("category", "other") if cls else "other",
            "summary": cls.get("summary", item["title"]) if cls else item["title"],
        })

    return classified, total_usage
