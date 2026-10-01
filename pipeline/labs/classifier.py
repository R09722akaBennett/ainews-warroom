"""Classify the labs' posts with Gemini, one batch per lab."""

from __future__ import annotations

import json

from rich.console import Console

from labs.llm import LLMUnavailable, call_llm
from prompts.labs_prompt import COMPETITOR_CLASSIFY_PROMPT

console = Console()

BATCH_SIZE = 30  # Max items per LLM call to avoid truncated responses


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON array from LLM response, handling markdown fences and truncation."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # A long batch can be cut off mid-array ("[{...},{...},{..."); keep the
    # objects that are complete.
    decoder = json.JSONDecoder()
    results = []
    pos = text.find("[")
    if pos == -1:
        raise json.JSONDecodeError("No JSON array found", text, 0)
    pos += 1

    while pos < len(text):
        while pos < len(text) and text[pos] in " ,\n\r\t":
            pos += 1
        if pos >= len(text) or text[pos] == "]":
            break
        try:
            obj, end_pos = decoder.raw_decode(text, pos)
            results.append(obj)
            pos = end_pos
        except json.JSONDecodeError:
            break

    if not results:
        raise json.JSONDecodeError("No valid JSON objects found", text, 0)
    return results


def _classify_chunk(
    company_name: str,
    domain: str,
    items: list[dict],
    index_offset: int,
) -> tuple[list[dict], dict | None]:
    """Classify one chunk of items; return the model's entries and the token usage.

    Entries carry the global index (index_offset plus the position in the
    chunk). An unreadable response or a Gemini outage returns no entries, so
    every item of the chunk stays pending.
    """
    lines = []
    for i, item in enumerate(items):
        idx = index_offset + i
        line = f"[{idx}] {item['title']}"
        if item.get("content"):
            # X posts are the lab's own words and short; give them more room than news snippets.
            limit = 600 if (item.get("source") or "").startswith("X @") else 300
            line += f"\n    {item['content'][:limit]}"
        lines.append(line)
    articles_text = "\n\n".join(lines)

    prompt = COMPETITOR_CLASSIFY_PROMPT.format(
        company_name=company_name,
        domain=domain,
        articles_text=articles_text,
    )

    try:
        text, token_usage = call_llm(prompt)
    except LLMUnavailable as e:
        console.print(f"    [red]Classification skipped, {len(items)} items stay pending: {e}[/]")
        return [], None
    try:
        classifications = _parse_json_response(text)
    except (json.JSONDecodeError, ValueError) as e:
        console.print(f"    [red]Classification parse error, {len(items)} items stay pending: {e}[/]")
        return [], token_usage
    if not isinstance(classifications, list):
        console.print(f"    [red]Classification is not a list, {len(items)} items stay pending[/]")
        return [], token_usage
    return [c for c in classifications if isinstance(c, dict)], token_usage


def classify_batch(
    company_name: str,
    domain: str,
    items: list[dict],
) -> tuple[list[dict], dict | None]:
    """Classify one lab's items in chunks of BATCH_SIZE.

    Returns:
        The items in input order and the summed token usage (None when no
        call reported any). An item the model classified gets ai_related,
        category and summary from the response. An item missing from the
        response, or in a chunk whose response could not be parsed, comes
        back unchanged with category "pending", so the caller must not write
        it and the next run classifies it again.
    """
    if not items:
        return [], None

    all_classifications: list[dict] = []
    total_usage: dict | None = None

    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start : start + BATCH_SIZE]
        if len(items) > BATCH_SIZE:
            console.print(f"    [dim]chunk {start // BATCH_SIZE + 1} ({start}–{start + len(chunk) - 1})[/]")

        classifications, token_usage = _classify_chunk(company_name, domain, chunk, start)
        all_classifications.extend(classifications)

        if token_usage:
            if total_usage is None:
                total_usage = {"input": 0, "output": 0, "total": 0}
            for k in ("input", "output", "total"):
                total_usage[k] += token_usage[k]

    by_index = {c.get("index"): c for c in all_classifications}
    classified = []
    for i, item in enumerate(items):
        cls = by_index.get(i)
        if cls is None:
            classified.append({**item, "category": "pending"})
            continue
        classified.append({
            **item,
            "ai_related": cls.get("ai_related", True),
            "category": cls.get("category", "other"),
            "summary": cls.get("summary", item["title"]),
        })

    return classified, total_usage
