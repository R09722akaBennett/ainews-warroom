"""Context gathering — loads all context needed for report generation."""

from __future__ import annotations

import os

from rich.console import Console

from db import get_recent_digests
from db.digests import DigestRecord

console = Console()

KDAN_CONTEXT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "kdan-context.md"
)


def load_recent_digests(days: int = 7) -> list[DigestRecord]:
    """Load recent daily digests for continuity context."""
    digests = get_recent_digests(days=days)
    console.print(f"  [green]✓[/] Recent digests: {len(digests)} days")
    return digests


def load_company_context() -> str:
    """Load KDAN Mobile company context from kdan-context.md."""
    if not os.path.exists(KDAN_CONTEXT_FILE):
        console.print("  [yellow]No kdan-context.md found[/]")
        return ""
    with open(KDAN_CONTEXT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    console.print(f"  [green]✓[/] Company context loaded ({len(content)} chars)")
    return content
