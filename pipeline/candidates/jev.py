"""Score candidates with TypeSafe Jev: importance, lab, category, same event.

Jev only judges; it writes no text. Dates and counts are handled in code
because the jev-1.13 docs list both as weak spots. The rubric is English
since CJK accuracy is documented as lower.
"""

from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait

from candidates import config

RUBRIC = (
    "Reader: an ML engineer who follows {interests}. "
    "Is this item important AI news that this reader would want to know about today?"
)
IMPORTANT_TRUE = ("A concrete model release, benchmark result, infrastructure or tooling launch, research "
                  "finding, funding or acquisition of an AI company, or an AI policy or safety event")
IMPORTANT_FALSE = ("Generic opinion, marketing, a tutorial or listicle, an event promotion, a hiring post, "
                   "or technology news that is not about AI")


def available() -> bool:
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def _field(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _questions(interests: str):
    from typesafe_sdk import Choice, Noul, NoulCriteria

    return {
        "important": Noul(instructions=RUBRIC.format(interests=interests),
                          criteria=NoulCriteria(true=IMPORTANT_TRUE, false=IMPORTANT_FALSE)),
        "lab_present": Noul(instructions="Is one AI lab or model company the primary subject of this item, "
                                         "not just mentioned in passing?"),
        "lab": Choice(instructions="Which AI lab or model company is the primary subject of this item?",
                      criteria=config.LABS),
        "category": Choice(instructions="What kind of event does this item report?", criteria=config.CATEGORIES),
    }


def _state(item: dict) -> dict:
    return {"title": item["title"], "source": item.get("source", ""), "snippet": item.get("snippet", "")}


def _score_one(client, questions, item):
    r = client.system_one(state=_state(item), questions=questions, model=config.JEV_MODEL,
                          timeout=config.JEV_CALL_TIMEOUT_S)
    a = _field(r, "answers", {}) or {}
    lab, cat = a.get("lab"), a.get("category")
    usage = _field(_field(r, "usage"), "input_tokens", 0) or 0
    return {
        "important": _field(a.get("important"), "noul"),
        "lab_present": _field(a.get("lab_present"), "noul"),
        "lab": _field(lab, "choice"),
        "lab_confidence": _field(lab, "confidence"),
        "category": _field(cat, "choice"),
        "category_confidence": _field(cat, "confidence"),
        "model": _field(r, "model"),
    }, usage


def _run_parallel(fn, items):
    """Apply fn to items with a deadline; return (results aligned to items, failures)."""
    results, failures = [None] * len(items), 0
    # No context manager: its exit would block on calls still in flight past
    # the deadline. Each call is bounded by JEV_CALL_TIMEOUT_S instead.
    pool = ThreadPoolExecutor(max_workers=config.JEV_WORKERS)
    futures = {pool.submit(fn, it): i for i, it in enumerate(items)}
    done, pending = wait(futures, timeout=config.JEV_DEADLINE_S)
    pool.shutdown(wait=False, cancel_futures=True)
    failures += len(pending)
    for f in done:
        try:
            results[futures[f]] = f.result()
        except Exception as e:  # noqa: BLE001
            failures += 1
            if failures <= 3:
                print(f"candidates: Jev call failed ({type(e).__name__}: {str(e)[:160]})")
    return results, failures


def score(items: list[dict], interests: str) -> dict:
    """Score items with Jev and attach the answers as item["jev"] in place.

    Returns:
        {status, calls, failures, input_tokens, seconds}; status is "degraded"
        when more than JEV_MAX_FAILURE_RATE of the calls failed or ran past
        the deadline, and the failed items have no "jev" key.
    """
    from typesafe_sdk import TypeSafeClient

    start = time.time()
    questions = _questions(interests)
    with TypeSafeClient() as client:
        results, failures = _run_parallel(lambda it: _score_one(client, questions, it), items)
    tokens = 0
    for it, res in zip(items, results):
        if res:
            it["jev"], used = res
            tokens += used
    rate = failures / len(items) if items else 0
    return {"status": "degraded" if rate > config.JEV_MAX_FAILURE_RATE else "ok", "calls": len(items),
            "failures": failures, "input_tokens": tokens, "seconds": round(time.time() - start, 1)}


def _words(title: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 3}


def same_event(items: list[dict], known: list[dict], per_item: int = 5, field: str = "dup_of") -> dict:
    """Mark item[field] when Jev says it reports the same event as a known item.

    known is either a fixed list (what the curated digest already covered) or
    None, meaning each item is compared with the items ranked above it, so
    only the highest-ranked copy of a story stays unmarked. Pairs are narrowed
    by title word overlap first so each item needs one request.
    """
    from typesafe_sdk import Noul, TypeSafeClient

    position = {id(it): i for i, it in enumerate(items)}

    def ask(it):
        pool_ = known if known is not None else items[: position[id(it)]]
        w = _words(it["title"])
        ranked = sorted(pool_, key=lambda k: len(w & _words(k["title"])), reverse=True)
        cands = [k for k in ranked[:per_item] if w & _words(k["title"])]
        if not cands:
            return None
        qs = {f"same_{i}": Noul(instructions={
            "known_event": {"title": k["title"], "source": k.get("source", "")},
            "question": "Does the item in state report the same underlying event as `known_event` "
                        "(the same announcement, paper, deal or incident), not merely the same topic?"})
              for i, k in enumerate(cands)}
        r = client.system_one(state=_state(it), questions=qs, model=config.JEV_MODEL,
                              timeout=config.JEV_CALL_TIMEOUT_S)
        a = _field(r, "answers", {}) or {}
        best = max(((i, _field(a.get(f"same_{i}"), "noul") or 0) for i in range(len(cands))), key=lambda x: x[1])
        return {"url": cands[best[0]]["url"], "title": cands[best[0]]["title"], "prob": best[1]}

    start = time.time()
    with TypeSafeClient() as client:
        results, failures = _run_parallel(ask, items)
    for it, res in zip(items, results):
        # 0.5: Jev's answer is a probability, so "more likely the same event than
        # not". No recorded reason beyond that; chosen by trial.
        it[field] = res if res and res["prob"] >= 0.5 else None
    return {"calls": len(items), "failures": failures, "seconds": round(time.time() - start, 1)}
