"""Export the running costs that are not LLM tokens to src/data/costs.json.

The analytics page already estimates Gemini from each report's tokenUsage;
this file adds the rest, per day since SITE_SINCE:

- X API: posts billed per UTC day, from data/x_state.json (labs/x_source.py).
- Jev: input tokens of the warroom candidates (data/candidates/<date>.json)
  and of the wiki radar (the daily note sidecar's jevUsage).
- Subscriptions: fixed yearly fees, spread evenly per month.

Prices are as published on 2026-10-01: X $0.005 per post read and $0.01 per
user lookup; Jev $0.042 per million input tokens, output free
(docs.typesafe.ai/models). The September X backfill ran before x_state
counted per day, so it is the one-off entry taken from the X console
(535 billable events, $2.79) and daily X counts start on 2026-10-02.

Usage:
    cd pipeline
    uv run --no-sync python -m export.costs
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "data" / "costs.json"
X_STATE = ROOT / "pipeline" / "data" / "x_state.json"
CANDIDATES = ROOT / "pipeline" / "data" / "candidates"
WIKI_NEWS = Path.home() / "wiki" / "notes" / "news"
SITE_SINCE = "2026-09-01"
X_DAILY_FROM = "2026-10-02"
PRICES = {"x_post": 0.005, "x_user_lookup": 0.01, "jev_per_mtok_input": 0.042}
SUBSCRIPTIONS = [{"name": "Latent Space（AINews 付費全文）", "usd_per_year": 69}]
ONE_OFF = [{"date": "2026-10-01", "item": "X", "label": "9 月官方貼文回補與 23 個帳號查詢",
            "usd": 2.79, "note": "X 後台 535 筆計費事件：512 則貼文、23 次帳號查詢"}]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main() -> None:
    days: dict[str, dict] = {}

    def day(d: str) -> dict:
        return days.setdefault(d, {"date": d, "x_posts_billed": 0, "jev_calls": 0, "jev_input_tokens": 0})

    for d, n in (_read_json(X_STATE).get("billed") or {}).items():
        if d >= X_DAILY_FROM:
            day(d)["x_posts_billed"] += int(n)
    for f in sorted(CANDIDATES.glob("*.json")):
        if f.stem >= SITE_SINCE:
            jev = _read_json(f).get("jev") or {}
            day(f.stem)["jev_calls"] += int(jev.get("calls") or 0)
            day(f.stem)["jev_input_tokens"] += int(jev.get("input_tokens") or 0)
    for f in sorted(WIKI_NEWS.glob("*.json")):
        if f.stem >= SITE_SINCE:
            jev = _read_json(f).get("jevUsage") or {}
            if jev:
                day(f.stem)["jev_calls"] += int(jev.get("calls") or 0)
                day(f.stem)["jev_input_tokens"] += int(jev.get("input_tokens") or 0)
    rows = []
    for d in sorted(days):
        r = days[d]
        r["x_usd"] = round(r["x_posts_billed"] * PRICES["x_post"], 4)
        r["jev_usd"] = round(r["jev_input_tokens"] / 1e6 * PRICES["jev_per_mtok_input"], 4)
        rows.append(r)
    DATA.write_text(json.dumps({
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": SITE_SINCE, "prices": PRICES, "subscriptions": SUBSCRIPTIONS,
        "oneOff": ONE_OFF, "days": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"costs: {len(rows)} days, X ${sum(r['x_usd'] for r in rows):.2f} + one-off "
          f"${sum(o['usd'] for o in ONE_OFF):.2f}, Jev ${sum(r['jev_usd'] for r in rows):.4f}")


if __name__ == "__main__":
    main()
