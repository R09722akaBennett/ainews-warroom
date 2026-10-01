"""Call Gemini for the labs tracker, retrying the failures that pass on their own."""

from __future__ import annotations

import os
import time

import google.genai as genai
import httpx
from google.genai import errors
from rich.console import Console

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Three attempts with 5 s and 10 s waits ride out a dropped connection or a
# brief overload without holding the cron job for long. No recorded reason
# for the exact values; chosen by trial.
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds, multiplied by the attempt number

_TRANSIENT_HTTP = (httpx.RemoteProtocolError, httpx.ReadTimeout, ConnectionError)


class EmptyResponse(Exception):
    """Gemini answered without text, e.g. when a safety filter blocked the candidate."""


class LLMUnavailable(Exception):
    """Gemini kept failing with transient errors until the retries ran out."""


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, (_TRANSIENT_HTTP, EmptyResponse, errors.ServerError)):
        return True
    # 429 is quota or rate limiting, which clears; other 4xx repeat on every attempt.
    return isinstance(exc, errors.ClientError) and exc.code == 429


def call_llm(prompt: str) -> tuple[str, dict | None]:
    """Send one prompt to Gemini and return its text with the token usage.

    Returns:
        The response text, never None, and {"input", "output", "total"} token
        counts, or None when the response carried no usage metadata.

    Raises:
        LLMUnavailable: Every attempt failed with a 5xx, a 429, a dropped
            connection, a read timeout or an empty response; the last error is
            chained as its cause.
        google.genai.errors.ClientError: Gemini rejected the request (4xx other
            than 429); retrying would get the same answer.
    """
    client = genai.Client()
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            if response.text is None:
                raise EmptyResponse("response has no text")
            token_usage = None
            um = getattr(response, "usage_metadata", None)
            if um:
                token_usage = {
                    "input": getattr(um, "prompt_token_count", 0) or 0,
                    "output": getattr(um, "candidates_token_count", 0) or 0,
                    "total": getattr(um, "total_token_count", 0) or 0,
                }
            return response.text, token_usage
        except Exception as e:  # noqa: BLE001
            if not _retryable(e):
                raise
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (attempt + 1)
                console.print(f"    [yellow]Retry {attempt + 1}/{MAX_RETRIES} after {delay}s ({type(e).__name__})[/]")
                time.sleep(delay)
    raise LLMUnavailable(f"Gemini failed {MAX_RETRIES} times: {type(last_exc).__name__}") from last_exc
