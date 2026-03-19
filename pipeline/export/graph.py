"""Build a tag co-occurrence graph from daily reports.

Produces src/data/graph.json with nodes (companies, models, topics)
and edges (co-occurrence within the same report), plus per-date tag lists
for time-based filtering on the frontend.
"""

from __future__ import annotations

import json
import os
from collections import Counter

from rich.console import Console

from db.connection import get_conn

console = Console()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "src", "data")


def export_graph() -> int:
    """Export tag co-occurrence graph to graph.json."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, tags FROM daily_digests WHERE tags IS NOT NULL ORDER BY date"
    ).fetchall()
    conn.close()

    # Collect all tag appearances and co-occurrences
    tag_count: Counter[str] = Counter()          # tag_id → total appearances
    tag_type: dict[str, str] = {}                # tag_id → type
    tag_label: dict[str, str] = {}               # tag_id → display label
    cooccurrence: Counter[tuple[str, str]] = Counter()  # (tag_a, tag_b) → count
    daily: dict[str, list[str]] = {}             # date → [tag_ids]
    report_dates: dict[str, list[str]] = {}      # tag_id → [dates]

    for row in rows:
        tags = json.loads(row["tags"]) if row["tags"] else {}
        date = row["date"]

        # Flatten all tags for this report
        all_tag_ids: list[str] = []
        for typ in ("companies", "models", "topics"):
            for tag_name in tags.get(typ, []):
                tid = f"{typ[:-3]}:{tag_name}"  # "company:openai", "model:gpt-5", "topic:agent"
                if typ == "companies":
                    tid = f"company:{tag_name}"
                elif typ == "models":
                    tid = f"model:{tag_name}"
                else:
                    tid = f"topic:{tag_name}"

                type_map = {"companies": "company", "models": "model", "topics": "topic"}
                tag_count[tid] += 1
                tag_type[tid] = type_map[typ]
                tag_label[tid] = tag_name
                all_tag_ids.append(tid)
                report_dates.setdefault(tid, []).append(date)

        daily[date] = all_tag_ids

        # Build co-occurrence edges (unique pairs within this report)
        unique_tags = sorted(set(all_tag_ids))
        for i in range(len(unique_tags)):
            for j in range(i + 1, len(unique_tags)):
                pair = (unique_tags[i], unique_tags[j])
                cooccurrence[pair] += 1

    # Build nodes — only include tags that appear >= 2 times
    min_count = 2
    active_tags = {tid for tid, cnt in tag_count.items() if cnt >= min_count}

    nodes = []
    for tid in sorted(active_tags):
        nodes.append({
            "id": tid,
            "label": tag_label[tid],
            "type": tag_type[tid],
            "count": tag_count[tid],
            "firstSeen": report_dates[tid][0],
            "lastSeen": report_dates[tid][-1],
        })

    # Build edges — only between active tags, weight >= 2
    min_weight = 2
    edges = []
    for (a, b), weight in cooccurrence.most_common():
        if a in active_tags and b in active_tags and weight >= min_weight:
            edges.append({
                "source": a,
                "target": b,
                "weight": weight,
            })

    # Daily tag lists (for time slider)
    daily_filtered = {
        date: [t for t in tids if t in active_tags]
        for date, tids in daily.items()
    }

    graph = {
        "nodes": nodes,
        "edges": edges,
        "daily": daily_filtered,
    }

    path = os.path.join(DATA_DIR, "graph.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False)

    console.print(
        f"  [green]✓[/] graph.json: {len(nodes)} nodes, {len(edges)} edges, "
        f"{len(daily_filtered)} days"
    )
    return len(nodes)
