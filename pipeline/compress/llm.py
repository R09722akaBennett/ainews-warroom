"""LLM compression — shared helpers for calling Gemini."""

from __future__ import annotations

import json
import os

import google.genai as genai

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def compress_with_llm(prompt: str) -> tuple[str, str, dict | None]:
    """Send prompt to Gemini and parse JSON response. Returns (title, content, tags)."""
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return parse_json_response(response.text)


def parse_json_response(text: str) -> tuple[str, str, dict | None]:
    """Parse a JSON response that may be wrapped in markdown fences.
    Returns (title, content, tags)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        result = json.loads(text)
        return result["title"], result["content"], result.get("tags")
    except (json.JSONDecodeError, KeyError):
        lines = text.split("\n", 1)
        title = lines[0].strip("# ").strip()
        content = lines[1].strip() if len(lines) > 1 else text
        return title, content, None
