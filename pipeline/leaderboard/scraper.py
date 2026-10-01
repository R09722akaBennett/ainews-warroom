"""Scrape the arena.ai leaderboard: one full table per category plus a cross-category text table."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")

BASE_URL = "https://arena.ai/leaderboard"

# Category slug → display label
CATEGORIES: dict[str, str] = {
    "text": "Text",
    "code": "Code",
    "vision": "Vision",
    "document": "Document",
    "text-to-image": "Text to Image",
    "image-edit": "Image Edit",
    "search": "Search",
    "text-to-video": "Text to Video",
    "image-to-video": "Image to Video",
}

# Model name prefix → org (fallback when SVG <title> is absent)
_ORG_PREFIXES: list[tuple[str, str]] = [
    ("gpt-", "OpenAI"),
    ("chatgpt-", "OpenAI"),
    ("gpt-image", "OpenAI"),
    ("o1-", "OpenAI"),
    ("o3-", "OpenAI"),
    ("o4-", "OpenAI"),
    ("dall-e-", "OpenAI"),
    ("gemini-", "Google"),
    ("gemma-", "Google"),
    ("veo-", "Google"),
    ("grok-", "xAI"),
    ("grok-imagine", "xAI"),
    ("claude-", "Anthropic"),
    ("llama-", "Meta"),
    ("mistral-", "Mistral"),
    ("mixtral-", "Mistral"),
    ("pixtral-", "Mistral"),
    ("codestral-", "Mistral"),
    ("command-", "Cohere"),
    ("command_", "Cohere"),
    ("qwen-", "Alibaba"),
    ("qwen2", "Alibaba"),
    ("deepseek-", "DeepSeek"),
    ("glm-", "Zhipu"),
    ("phi-", "Microsoft"),
    ("wizardlm-", "Microsoft"),
    ("yi-", "01.AI"),
    ("dbrx", "Databricks"),
    ("jamba-", "AI21"),
    ("reka-", "Reka"),
    ("flux-", "Black Forest Labs"),
    ("ideogram-", "Ideogram"),
    ("stable-diffusion", "Stability"),
    ("playground-", "Playground"),
    ("amazon-", "Amazon"),
    ("nova-", "Amazon"),
    ("dola-", "ByteDance"),
]


def _infer_org(model: str) -> str:
    """Return the org whose model-name prefix matches model, or ""."""
    lower = model.lower()
    for prefix, org in _ORG_PREFIXES:
        if lower.startswith(prefix):
            return org
    return ""


def _parse_int(text: str) -> int:
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0


def _parse_score_cell(cell) -> tuple[int, str]:
    """Return (score, ci) from a Score cell, e.g. (1525, "±9").

    arena.ai renames its utility classes between releases (`text-sm` became
    `body-sm`, which silently zeroed every score), so the cell is read by
    shape instead: the first span holding a bare integer is the score and the
    first span starting with "±" is the confidence interval.
    """
    score, ci = 0, ""
    for span in cell.find_all("span"):
        text = span.get_text(strip=True)
        if not score and re.fullmatch(r"\d[\d,]*", text):
            score = _parse_int(text)
        elif not ci and text.startswith("±"):
            ci = text
    return score, ci


def _parse_category_page(html: str) -> list[dict]:
    """Return one row per model from a category leaderboard page.

    Columns vary by category; most tabs have Rank, Rank Spread, Model,
    Score (±CI) and Votes, and some add Price ($/M) and Context.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if not tables:
        return []

    table = tables[0]
    ths = table.select("th")
    headers = [th.get_text(strip=True).lower() for th in ths]

    def col_idx(name: str) -> int | None:
        for i, h in enumerate(headers):
            if name in h:
                return i
        return None

    idx_rank = col_idx("rank")
    idx_spread = col_idx("spread")
    idx_score = col_idx("score")
    idx_votes = col_idx("votes")
    idx_price = col_idx("price")
    idx_context = col_idx("context")

    # The model header is empty or an icon on some tabs, so it cannot be
    # found by name; every tab puts it third (Rank, Rank Spread, Model).
    idx_model = 2

    rows = []
    for tr in table.select("tr"):
        cells = tr.find_all("td")
        if not cells or len(cells) < 4:
            continue

        rank_text = cells[idx_rank].get_text(strip=True) if idx_rank is not None else ""
        try:
            rank = int(rank_text.replace("#", ""))
        except ValueError:
            continue

        model_cell = cells[idx_model]
        svg_title = model_cell.select_one("svg title")
        org = svg_title.get_text(strip=True) if svg_title else ""

        a_tag = model_cell.select_one("a")
        model_span = model_cell.select_one("span.truncate")
        model = ""
        if a_tag:
            model = a_tag.get_text(strip=True)
        elif model_span:
            model = model_span.get_text(strip=True)
        else:
            full_text = model_cell.get_text(strip=True)
            model = full_text[len(org):] if org and full_text.startswith(org) else full_text

        license_span = model_cell.select_one("span.text-text-secondary")
        provider_text = license_span.get_text(strip=True) if license_span else ""
        # Format: "Anthropic · Proprietary" or "Meta · Open"
        license_type = ""
        if " · " in provider_text:
            parts = provider_text.split(" · ", 1)
            if not org:
                org = parts[0].strip()
            license_type = parts[1].strip() if len(parts) > 1 else ""

        if not org:
            org = _infer_org(model)

        rank_spread = _parse_int(cells[idx_spread].get_text(strip=True)) if idx_spread is not None else None

        score = 0
        ci = ""
        if idx_score is not None:
            score, ci = _parse_score_cell(cells[idx_score])

        votes = _parse_int(cells[idx_votes].get_text(strip=True)) if idx_votes is not None else 0

        price = ""
        if idx_price is not None and idx_price < len(cells):
            price = cells[idx_price].get_text(strip=True)
            if price == "N/A":
                price = ""

        context = ""
        if idx_context is not None and idx_context < len(cells):
            context = cells[idx_context].get_text(strip=True)
            if context == "N/A":
                context = ""

        entry: dict = {
            "rank": rank,
            "model": model,
            "org": org,
            "score": score,
            "votes": votes,
        }
        if ci:
            entry["ci"] = ci
        if rank_spread is not None:
            entry["rankSpread"] = rank_spread
        if license_type:
            entry["license"] = license_type
        if price:
            entry["price"] = price
        if context:
            entry["context"] = context

        rows.append(entry)

    return rows


def _parse_overview_full_table(html: str) -> list[dict]:
    """Return one row per model from the full rankings table of the main /leaderboard page.

    The columns are Model, Overall, Expert, Hard Prompts, Coding, Math,
    Creative Writing, Instruction Following and Longer Query.
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table")
    if not tables:
        return []

    big_table = tables[-1]

    ths = big_table.select("th")
    headers = [th.get_text(strip=True) for th in ths]
    if headers:
        headers[0] = "model"
    col_names = []
    for h in headers:
        key = re.sub(r"\d+/\d+", "", h).strip()
        col_names.append(key.lower().replace(" ", "_") if key else "model")

    rows = []
    for tr in big_table.select("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue

        model_cell = cells[0]
        svg_title = model_cell.select_one("svg title")
        org = svg_title.get_text(strip=True) if svg_title else ""
        a_tag = model_cell.select_one("a")
        model_span = model_cell.select_one("span.truncate")
        if a_tag:
            model = a_tag.get_text(strip=True)
        elif model_span:
            model = model_span.get_text(strip=True)
        else:
            full_text = model_cell.get_text(strip=True)
            model = full_text[len(org):] if org and full_text.startswith(org) else full_text

        if not org:
            org = _infer_org(model)

        entry: dict = {"model": model, "org": org}

        for i, cell in enumerate(cells[1:], 1):
            if i < len(col_names):
                val = cell.get_text(strip=True)
                entry[col_names[i]] = _parse_int(val) if val else None

        rows.append(entry)

    return rows


# full-table column → text sub-category slug ("" is the overall text ranking)
TEXT_SUBCATEGORIES = {
    "overall": "",
    "expert": "expert",
    "hard_prompts": "hard-prompts",
    "coding": "coding",
    "math": "math",
    "creative_writing": "creative-writing",
    "instruction_following": "instruction-following",
    "longer_query": "longer-query",
}


def _fetch_full_table(headers: dict) -> list[dict]:
    """Return one row per text model with its rank in each sub-category."""
    ranks: dict[str, dict[str, int]] = {}
    for column, sub in TEXT_SUBCATEGORIES.items():
        url = f"{BASE_URL}/text/{sub}".rstrip("/")
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        rows = _parse_category_page(resp.text)
        if column == "overall" and not rows:
            return []
        for r in rows:
            entry = ranks.setdefault(r["model"], {"model": r["model"], "org": r.get("org", "")})
            entry[column] = r.get("rank")
    full = [r for r in ranks.values() if r.get("overall") is not None]
    for r in full:
        for column in TEXT_SUBCATEGORIES:
            r.setdefault(column, None)
    return sorted(full, key=lambda r: r["overall"])


def fetch_leaderboard() -> dict:
    """Fetch the arena.ai leaderboard: one request per category plus the text sub-category pages."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    categories: dict[str, list[dict]] = {}

    for slug, label in CATEGORIES.items():
        url = f"{BASE_URL}/{slug}"
        console.print(f"  Fetching [cyan]{label}[/] ({slug})...", end=" ")
        try:
            resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            rows = _parse_category_page(resp.text)
            categories[slug] = rows
            console.print(f"[green]{len(rows)} models[/]")
        except Exception as e:
            console.print(f"[red]error: {e}[/]")
            categories[slug] = []

    # Cross-category table. arena.ai dropped the overview <table>, so build it
    # from the text leaderboard plus one page per text sub-category, keyed by
    # model name.
    console.print("  Fetching [cyan]text sub-categories[/] (full table)...", end=" ")
    try:
        full = _fetch_full_table(headers)
        console.print(f"[green]{len(full)} models[/]")
    except Exception as e:
        console.print(f"[red]error: {e}[/]")
        full = []

    return {
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categoryLabels": {k: v for k, v in CATEGORIES.items()},
        "categories": categories,
        "full": full,
    }


def main() -> bool:
    """Refresh the JSON file; return False when it was left untouched."""
    console.print("\n[bold]Fetching Arena AI Leaderboard...[/]\n")

    try:
        data = fetch_leaderboard()
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        console.print("[yellow]Keeping existing leaderboard.json if present.[/]")
        return False

    total = len(data["full"]) + sum(len(v) for v in data["categories"].values())
    if total == 0:
        console.print("[yellow]Warning: no data extracted. Page structure may have changed.[/]")
        return False

    # The home page requires `full`, and an empty category tab looks broken,
    # so a part that failed keeps its previous data and the run reports failure.
    path = os.path.join(DATA_DIR, "leaderboard.json")
    try:
        with open(path, encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, json.JSONDecodeError):
        previous = {}
    stale = []
    if not data["full"] and previous.get("full"):
        data["full"] = previous["full"]
        stale.append("full")
    for slug, rows in data["categories"].items():
        if not rows and previous.get("categories", {}).get(slug):
            data["categories"][slug] = previous["categories"][slug]
            stale.append(slug)
    if stale:
        console.print(f"[yellow]Warning: kept previous data for {', '.join(stale)}.[/]")

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    cat_total = sum(len(v) for v in data["categories"].values())
    console.print(
        f"\n[bold green]Done! {cat_total} category entries + "
        f"{len(data['full'])} full rankings → src/data/leaderboard.json[/]"
    )
    return not stale


if __name__ == "__main__":
    main()
