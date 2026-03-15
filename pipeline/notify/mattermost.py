"""Send daily report to Mattermost via Bot API.

Environment variables:
    MATTERMOST_URL        — Server URL, e.g. https://chat.example.com
    MATTERMOST_BOT_TOKEN  — Bot access token
    MATTERMOST_CHANNEL_ID — Target channel ID
"""

from __future__ import annotations

import os
import re

import httpx
from rich.console import Console

from db import init_db
from db.connection import get_conn
from export.site import strip_frontmatter

console = Console()

SITE_URL = "https://ainews-warroom.vercel.app"


def _get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val


def get_today_report(date: str | None = None) -> tuple[dict, str] | None:
    """Read today's report from DB. Returns (row_dict, cleaned_content) or None."""
    init_db()
    conn = get_conn()

    if date:
        row = conn.execute(
            "SELECT date, title, insights FROM daily_digests WHERE date = ?",
            (date,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT date, title, insights FROM daily_digests ORDER BY date DESC LIMIT 1"
        ).fetchone()
    conn.close()

    if not row:
        return None

    content = strip_frontmatter(row["insights"])
    return dict(row), content


def _downgrade_headings(text: str) -> str:
    """Downgrade markdown headings by 2 levels for Mattermost readability."""
    return re.sub(r"^(#{1,4}) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", text, flags=re.MULTILINE)


def format_message(row: dict, content: str) -> str:
    """Format the full Mattermost message with header and footer."""
    date = row["date"]
    report_url = f"{SITE_URL}/reports/{date}"

    header = (
        f":globe_with_meridians: [AI War Room Dashboard]({SITE_URL})"
        f"| :bar_chart: [完整報告與歷史資料]({report_url})\n"
        f":rotating_light: KDAN AI 戰情報告 ({date})\n"
    )

    # Remove duplicate title if insights already starts with # title
    body = content
    first_line_end = body.find("\n")
    if first_line_end != -1:
        first_line = body[:first_line_end].strip()
        if first_line.startswith("# ") and "戰情報告" in first_line:
            body = body[first_line_end:].lstrip("\n")

    return header + _downgrade_headings(body)


def send_to_mattermost(message: str) -> None:
    """Post a message to Mattermost channel using Bot API."""
    url = _get_env("MATTERMOST_URL").rstrip("/")
    token = _get_env("MATTERMOST_BOT_TOKEN")
    channel_id = _get_env("MATTERMOST_CHANNEL_ID")

    endpoint = f"{url}/api/v4/posts"

    resp = httpx.post(
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
        json={"channel_id": channel_id, "message": message},
        timeout=30,
    )
    resp.raise_for_status()
    console.print(f"  [green]✓[/] Posted to Mattermost (channel {channel_id})")


def main(date: str | None = None) -> None:
    result = get_today_report(date)
    if not result:
        console.print("[yellow]No report found to send.[/]")
        return

    row, content = result
    message = format_message(row, content)

    char_count = len(message)
    console.print(f"  Report length: {char_count} chars (limit: 16383)")

    if char_count > 16383:
        console.print("[yellow]Report exceeds limit, splitting into sections...[/]")
        _send_split(row, content)
    else:
        send_to_mattermost(message)


def _send_split(row: dict, content: str) -> None:
    """Split report by ## sections and send each as a separate message."""
    date = row["date"]
    report_url = f"{SITE_URL}/reports/{date}"

    # Remove duplicate title from content
    body = content
    first_line_end = body.find("\n")
    if first_line_end != -1:
        first_line = body[:first_line_end].strip()
        if first_line.startswith("# ") and "戰情報告" in first_line:
            body = body[first_line_end:].lstrip("\n")

    lines = body.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("## ") and current:
            sections.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current))

    header = (
        f":bar_chart: [完整報告與歷史資料]({report_url}) "
        f"| :globe_with_meridians: [AI War Room Dashboard]({SITE_URL})\n"
        f"### :rotating_light: KDAN AI 戰情報告 ({date})\n"
    )

    for i, section in enumerate(sections, 1):
        msg = _downgrade_headings(section.strip())
        if i == 1:
            msg = header + msg
        console.print(f"  Sending part {i}/{len(sections)} ({len(msg)} chars)...")
        send_to_mattermost(msg)
