"""Raw exporter — saves all collected news items as markdown for audit trail."""

from __future__ import annotations

import os
from datetime import datetime

import yaml

from models import NewsItem
from config import OUTPUT_DIR


def _group_by_source(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = {}
    for item in items:
        groups.setdefault(item.source_name, []).append(item)
    return groups


def _extract_tags(items: list[NewsItem]) -> dict[str, list[str]]:
    tag_keywords = {
        "companies": [
            "openai", "anthropic", "google", "deepmind", "meta", "microsoft",
            "nvidia", "mistral", "hugging face", "cohere", "perplexity",
            "cursor", "vercel", "langchain", "xai", "deepseek", "groq",
            "together", "replicate", "stability", "midjourney", "adobe",
        ],
        "models": [
            "gpt", "claude", "gemini", "llama", "mistral", "whisper",
            "stable diffusion", "dall-e", "sora", "flux",
        ],
        "topics": [
            "agent", "rag", "fine-tuning", "quantization", "embedding",
            "multimodal", "reasoning", "inference", "benchmark",
            "open source", "transformer", "diffusion", "rlhf",
            "context window", "vision", "coding", "safety",
        ],
    }

    found: dict[str, set[str]] = {k: set() for k in tag_keywords}
    for item in items:
        text = f"{item.title} {item.content[:200]}".lower()
        for category, keywords in tag_keywords.items():
            for kw in keywords:
                if kw in text:
                    found[category].add(kw.replace(" ", "-"))

    return {k: sorted(v) for k, v in found.items() if v}


def export_raw_markdown(items: list[NewsItem], date: str) -> str:
    """Export all raw news items as a single markdown file. Returns file path."""
    dt = datetime.strptime(date, "%Y-%m-%d")
    short_date = dt.strftime("%y-%m-%d")
    filename = f"{short_date}-raw-sources.md"

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    tags = _extract_tags(items)
    groups = _group_by_source(items)

    source_summary = ", ".join(
        f"{src} ({len(group)})"
        for src, group in sorted(groups.items(), key=lambda x: -len(x[1]))
    )

    frontmatter: dict = {
        "title": f"AI 原始資訊彙整 ({date})",
        "description": f"從 {len(groups)} 個來源收集 {len(items)} 條 AI 相關資訊。來源: {source_summary[:300]}",
        "date": f"{date}T00:00:00.000Z",
        "draft": True,
    }
    for key in ("companies", "models", "topics"):
        if tags.get(key):
            frontmatter[key] = tags[key]

    lines: list[str] = []
    lines.append("---")
    lines.append(yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip())
    lines.append("---")
    lines.append("")
    lines.append(f"# AI 原始資訊彙整 ({date})")
    lines.append("")
    lines.append(f"> 共收集 **{len(items)}** 條資訊，來自 **{len(groups)}** 個來源。")
    lines.append("")

    # Table of contents
    lines.append("## 來源概覽")
    lines.append("")
    lines.append("| 來源 | 數量 |")
    lines.append("|------|------|")
    for src, group in sorted(groups.items(), key=lambda x: -len(x[1])):
        anchor = src.lower().replace(" ", "-").replace("/", "")
        lines.append(f"| [{src}](#{anchor}) | {len(group)} |")
    lines.append("")

    for src, group in sorted(groups.items(), key=lambda x: -len(x[1])):
        lines.append(f"## {src}")
        lines.append("")
        group.sort(key=lambda x: x.score, reverse=True)

        for i, item in enumerate(group, 1):
            lines.append(f"### {i}. [{item.title}]({item.url})")
            lines.append("")

            meta_parts = []
            if item.score:
                meta_parts.append(f"Score: **{item.score}**")
            if item.comments_count:
                meta_parts.append(f"Comments: {item.comments_count}")
            if item.published_at:
                meta_parts.append(f"Published: {item.published_at.strftime('%Y-%m-%d %H:%M')}")
            if meta_parts:
                lines.append(f"*{' | '.join(meta_parts)}*")
                lines.append("")

            if item.content:
                content = item.content.strip().replace("\n", " ")[:500]
                lines.append(f"> {content}")
                lines.append("")

            if item.metadata:
                extras = []
                if "authors" in item.metadata:
                    extras.append(f"Authors: {', '.join(item.metadata['authors'][:5])}")
                if "total_stars" in item.metadata:
                    extras.append(f"Total stars: {item.metadata['total_stars']:,}")
                if "language" in item.metadata:
                    extras.append(f"Language: {item.metadata['language']}")
                if "subreddit" in item.metadata:
                    extras.append(f"Subreddit: r/{item.metadata['subreddit']}")
                if "categories" in item.metadata:
                    cats = item.metadata["categories"]
                    if isinstance(cats, list):
                        extras.append(f"Categories: {', '.join(str(c) for c in cats[:5])}")
                if extras:
                    lines.append(f"*{' | '.join(extras)}*")
                    lines.append("")

        lines.append("---")
        lines.append("")

    lines.append(f"*自動收集於 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC*")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
