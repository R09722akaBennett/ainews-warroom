"""LLM translation for IDP Community items."""

from __future__ import annotations

import json
import os
import re
import time

import google.genai as genai
import httpx
from rich.console import Console

from prompts.idp_prompt import IDP_WEEKLY_RECAP_PROMPT, IDP_OPINION_PROMPT

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
MAX_RETRIES = 3
RETRY_DELAY = 5
MAX_TEXT_CHARS = 30000  # safety cap on raw_text

_RETRYABLE = (httpx.RemoteProtocolError, httpx.ReadTimeout, ConnectionError)


def _call_llm(prompt: str) -> tuple[str, dict | None]:
    client = genai.Client()
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            usage = None
            um = getattr(response, "usage_metadata", None)
            if um:
                usage = {
                    "input": getattr(um, "prompt_token_count", 0) or 0,
                    "output": getattr(um, "candidates_token_count", 0) or 0,
                    "total": getattr(um, "total_token_count", 0) or 0,
                }
            return response.text, usage
        except _RETRYABLE as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to locate the first {...} block
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def translate_item(item: dict) -> tuple[dict | None, dict | None]:
    """Translate a single IDP item. Returns (parsed_dict, token_usage) or (None, None) on failure."""
    kind = item["kind"]
    if kind == "weekly_recap":
        template = IDP_WEEKLY_RECAP_PROMPT
    elif kind == "opinion":
        template = IDP_OPINION_PROMPT
    else:
        return None, None  # plain news items not LLM-translated

    raw_text = (item.get("raw_text") or "")[:MAX_TEXT_CHARS]
    prompt = template.format(
        url=item.get("url", ""),
        title=item.get("title", ""),
        published_at=item.get("published_at") or "",
        raw_text=raw_text,
    )

    try:
        text, usage = _call_llm(prompt)
        parsed = _parse_json(text)
        return parsed, usage
    except Exception as e:
        console.print(f"    [red]LLM error for {item.get('title')[:60]}: {e}[/]")
        return None, None
