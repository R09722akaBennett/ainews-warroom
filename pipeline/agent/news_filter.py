"""LLM-based news filtering — deduplicates and selects top items from large batches."""

from __future__ import annotations

import json
import os

import google.genai as genai
from rich.console import Console

from models import NewsItem

console = Console()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

FILTER_PROMPT = """你是一位 AI 新聞編輯。以下是從 Google News 收集到的新聞標題列表。

請執行兩個任務：
1. **去重**：多篇報導同一事件的新聞，只保留最具代表性的一篇（標題最完整、來源最權威的）
2. **篩選**：保留所有重要的 AI 相關新聞，移除明顯不相關或低價值的項目

回傳要保留的項目編號（JSON 陣列），例如：[0, 2, 5, 8, 12]

重要原則：
- 寧可多留，不可漏掉重要新聞
- 同一事件只保留 1 篇，但不同面向的報導（如技術分析 vs 商業影響）可各保留 1 篇
- 非 AI 相關的新聞直接移除
- 目標數量：保留約 30 條最重要的新聞

## 新聞列表
"""


def filter_google_news(items: list[NewsItem]) -> list[NewsItem]:
    """Use LLM to deduplicate and filter Google News items.

    Returns the filtered subset of items.
    """
    if len(items) <= 30:
        return items

    # Build the item list for the prompt
    lines = []
    for i, item in enumerate(items):
        via = item.metadata.get("via", "") if item.metadata else ""
        source_info = f" (via {via})" if via else ""
        lines.append(f"[{i}] {item.title}{source_info}")

    prompt = FILTER_PROMPT + "\n".join(lines)

    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[{"role": "user", "parts": [{"text": prompt}]}],
    )

    # Parse response — expect a JSON array of indices
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        keep_indices = json.loads(text)
        if not isinstance(keep_indices, list):
            console.print("[red]Filter LLM returned non-list, keeping all items[/]")
            return items
    except json.JSONDecodeError:
        console.print("[red]Filter LLM returned invalid JSON, keeping all items[/]")
        return items

    # Filter — only keep valid indices
    valid = {i for i in keep_indices if isinstance(i, int) and 0 <= i < len(items)}
    filtered = [items[i] for i in sorted(valid)]

    console.print(f"    [cyan]Google News filtered: {len(items)} → {len(filtered)}[/]")

    return filtered
