"""Context gathering — loads all context needed for report generation."""

from __future__ import annotations

import os

from rich.console import Console

from db import get_recent_digests, get_latest_summaries
from db.digests import DigestRecord
from db.summaries import SummaryRecord

console = Console()

KDAN_CONTEXT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "kdan-context.md"
)


def load_recent_digests(days: int = 7) -> list[DigestRecord]:
    """Load recent daily digests for continuity context."""
    digests = get_recent_digests(days=days)
    console.print(f"  [green]✓[/] Recent digests: {len(digests)} days")
    return digests


def load_compressed_history() -> dict[str, SummaryRecord | None]:
    """Load latest weekly/monthly/quarterly summaries."""
    summaries = get_latest_summaries()
    found = [k for k, v in summaries.items() if v]
    if found:
        console.print(f"  [green]✓[/] Compressed history: {', '.join(found)}")
    else:
        console.print("  [dim]No compressed history yet (expected on first runs)[/]")
    return summaries


def load_company_context() -> str:
    """Load KDAN Mobile company context from kdan-context.md."""
    if not os.path.exists(KDAN_CONTEXT_FILE):
        console.print("  [yellow]No kdan-context.md found[/]")
        return ""
    with open(KDAN_CONTEXT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    console.print(f"  [green]✓[/] Company context loaded ({len(content)} chars)")
    return content
