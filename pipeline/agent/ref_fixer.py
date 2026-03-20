"""Post-processing ref fixer — corrects hallucinated ref-N indices in reports.

The LLM often assigns wrong ref-N numbers. This module extracts each section
of the report, matches it against the actual newsItems by keyword overlap,
and replaces incorrect refs with the correct indices.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from rich.console import Console

from models import NewsItem

console = Console()

# Words too common to be useful for matching
_STOPWORDS = {
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "as", "into", "about",
    "that", "this", "it", "its", "or", "and", "but", "if", "not", "no",
    "so", "up", "out", "than", "how", "all", "each", "every", "both",
    "new", "first", "also", "more", "most", "very", "just", "over",
    "after", "before", "between", "through", "during", "where", "when",
    "what", "which", "who", "why", "their", "our", "your",
    # Chinese common
    "的", "了", "在", "是", "和", "與", "為", "將", "對", "從", "到",
    "以", "及", "被", "讓", "把", "而", "也", "都", "則", "等", "於",
    "其", "中", "上", "下", "已", "更", "最", "再", "還", "又", "或",
    "並", "但", "卻", "所", "這", "那", "此", "該", "每", "各",
}


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text (Chinese chars + English words)."""
    text = text.lower()
    # Remove markdown formatting
    text = re.sub(r'\*\*|__|##|###', '', text)
    # Remove ref markers
    text = re.sub(r'ref-\d+', '', text)

    tokens = set()

    # English words (3+ chars)
    for word in re.findall(r'[a-z][a-z0-9.+-]+', text):
        if word not in _STOPWORDS and len(word) >= 3:
            tokens.add(word)

    # Chinese characters — use bigrams for better matching
    chinese = re.findall(r'[\u4e00-\u9fff]+', text)
    for segment in chinese:
        for i in range(len(segment) - 1):
            bigram = segment[i:i+2]
            if bigram not in _STOPWORDS:
                tokens.add(bigram)

    # Numbers (significant ones like dollar amounts, percentages)
    for num in re.findall(r'\d[\d,.]+', text):
        if len(num) >= 2:
            tokens.add(num)

    return tokens


def _parse_sections(markdown: str) -> list[dict]:
    """Parse markdown into sections, each with headline, body, and ref numbers."""
    sections = []
    lines = markdown.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith('### ') and 'ref-' in line:
            # Extract refs from headline
            refs = [int(x) for x in re.findall(r'ref-(\d+)', line)]
            headline = line

            # Collect body until next headline or section divider
            body_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('### ') and not lines[i].startswith('## ') and not lines[i].startswith('---'):
                body_lines.append(lines[i])
                i += 1

            sections.append({
                'headline': headline,
                'body': '\n'.join(body_lines),
                'refs': refs,
                'line_start': headline,
            })
        else:
            i += 1

    return sections


def _find_best_matches(section_text: str, items: list[NewsItem], n: int) -> list[int]:
    """Find the top N newsItem indices that best match the section text."""
    section_tokens = _tokenize(section_text)
    if not section_tokens:
        return []

    scores: list[tuple[float, int]] = []
    for idx, item in enumerate(items):
        item_text = f"{item.title} {item.source_name}"
        if item.content:
            item_text += f" {item.content[:500]}"
        item_tokens = _tokenize(item_text)

        if not item_tokens:
            continue

        # Jaccard-like overlap, weighted toward section coverage
        overlap = section_tokens & item_tokens
        if not overlap:
            continue

        score = len(overlap) / min(len(section_tokens), len(item_tokens))
        scores.append((score, idx))

    # Sort by score descending, take top N
    scores.sort(key=lambda x: (-x[0], x[1]))
    return [idx for _, idx in scores[:n]]


def fix_refs(markdown: str, items: list[NewsItem]) -> str:
    """Fix hallucinated ref-N numbers in the report markdown.

    For each section with refs, finds the best matching newsItems
    and replaces the ref numbers accordingly.
    """
    if not items:
        return markdown

    sections = _parse_sections(markdown)
    if not sections:
        return markdown

    replacements: dict[str, str] = {}
    fixed_count = 0
    total_refs = 0

    for section in sections:
        total_refs += len(section['refs'])
        section_text = section['headline'] + '\n' + section['body']
        n_refs = len(section['refs'])

        best_matches = _find_best_matches(section_text, items, n_refs)

        if not best_matches:
            continue

        # Build replacement for the headline
        old_headline = section['headline']
        # Remove old refs from headline
        headline_no_refs = re.sub(r'\s*ref-\d+[,\s]*', ' ', old_headline).rstrip()
        headline_no_refs = re.sub(r'\s+$', '', headline_no_refs)
        # Append corrected refs
        ref_str = ', '.join(f'ref-{idx}' for idx in best_matches)
        new_headline = f"{headline_no_refs} {ref_str}"

        if old_headline != new_headline:
            replacements[old_headline] = new_headline
            fixed_count += len(section['refs'])

    # Also fix refs in body text (市場洞察, 戰略洞察 sections)
    # Find inline refs like (ref-123) or (ref-1, ref-45) in non-headline lines
    def _fix_inline_ref(match: re.Match) -> str:
        full = match.group(0)
        ref_nums = [int(x) for x in re.findall(r'ref-(\d+)', full)]
        # For inline refs, we can't easily determine context, so leave them
        # if they're within valid range
        if all(0 <= r < len(items) for r in ref_nums):
            return full
        return full  # Keep as-is for now, headline fixes are the priority

    # Apply headline replacements
    result = markdown
    for old, new in replacements.items():
        result = result.replace(old, new, 1)

    console.print(f"  [cyan]Ref fixer: {fixed_count}/{total_refs} refs corrected across {len(replacements)} headlines[/]")

    return result
