"""Frontier AI labs to track: queries, feeds and display attributes.

Replaced the KDAN competitor list on 2026-10-01. Tier 1 labs get their own
summary in the weekly report; tier 2 labs are collected the same way but only
appear in the report's overview. region is where the lab is headquartered;
openness describes its flagship models (open weights, closed, or both).
Seeded from the organizations on the arena.ai leaderboard.
"""

from __future__ import annotations

from config import RSS_FEEDS


def _q(*names: str, extra: str = "AI OR model OR LLM") -> list[str]:
    alts = " OR ".join(f'"{n}"' for n in names)
    return [f"({alts}) ({extra}) when:3d"]


def _feeds(*names: str) -> dict[str, str]:
    return {n: RSS_FEEDS[n] for n in names if n in RSS_FEEDS}


LABS: dict[str, dict] = {
    # --- Tier 1 ---------------------------------------------------------
    "openai": {"name": "OpenAI", "tier": 1, "region": "us", "openness": "closed",
               "google_queries": _q("OpenAI"), "rss_feeds": _feeds("OpenAI Blog")},
    "anthropic": {"name": "Anthropic", "tier": 1, "region": "us", "openness": "closed",
                  "google_queries": _q("Anthropic"), "rss_feeds": _feeds("Anthropic News", "Anthropic Research")},
    "google_deepmind": {"name": "Google DeepMind", "tier": 1, "region": "us", "openness": "mixed",
                        "google_queries": _q("Google DeepMind", "Gemini model"),
                        "rss_feeds": _feeds("Google DeepMind", "Google AI Blog")},
    "xai": {"name": "xAI", "tier": 1, "region": "us", "openness": "closed",
            "google_queries": _q("xAI", "Grok"), "rss_feeds": _feeds("xAI News")},
    "meta": {"name": "Meta AI", "tier": 1, "region": "us", "openness": "mixed",
             "google_queries": _q("Meta AI", "Meta Superintelligence", "Llama model"),
             "rss_feeds": _feeds("Meta AI Blog")},
    "thinking_machines": {"name": "Thinking Machines", "tier": 1, "region": "us", "openness": "closed",
                          "google_queries": _q("Thinking Machines Lab", "Mira Murati", extra="AI OR startup OR model")},
    "deepseek": {"name": "DeepSeek", "tier": 1, "region": "china", "openness": "open",
                 "google_queries": _q("DeepSeek")},
    "alibaba_qwen": {"name": "Alibaba Qwen", "tier": 1, "region": "china", "openness": "open",
                     "google_queries": _q("Qwen", "Alibaba Cloud AI", "Tongyi")},
    "zhipu": {"name": "Zhipu (Z.ai)", "tier": 1, "region": "china", "openness": "open",
              "google_queries": _q("Zhipu", "Z.ai", "GLM model")},
    "moonshot": {"name": "Moonshot AI", "tier": 1, "region": "china", "openness": "open",
                 "google_queries": _q("Moonshot AI", "Kimi")},
    "bytedance_seed": {"name": "ByteDance Seed", "tier": 1, "region": "china", "openness": "mixed",
                       "google_queries": _q("ByteDance Seed", "Doubao", "ByteDance AI")},
    "mistral": {"name": "Mistral AI", "tier": 1, "region": "europe", "openness": "open",
                "google_queries": _q("Mistral AI"), "rss_feeds": _feeds("Mistral AI News")},
    # --- Tier 2 ---------------------------------------------------------
    "microsoft_ai": {"name": "Microsoft AI", "tier": 2, "region": "us", "openness": "mixed",
                     "google_queries": _q("Microsoft AI", "Mustafa Suleyman"), "rss_feeds": _feeds("Microsoft AI Blog")},
    "nvidia": {"name": "NVIDIA", "tier": 2, "region": "us", "openness": "open",
               "google_queries": _q("Nvidia Nemotron", "Nvidia AI model"), "rss_feeds": _feeds("NVIDIA AI Blog")},
    "ai2": {"name": "Ai2", "tier": 2, "region": "us", "openness": "open",
            "google_queries": _q("Allen Institute for AI", "Ai2 OLMo")},
    "ssi": {"name": "Safe Superintelligence", "tier": 2, "region": "us", "openness": "closed",
            "google_queries": _q("Safe Superintelligence", "Ilya Sutskever", extra="AI OR startup")},
    "reflection": {"name": "Reflection AI", "tier": 2, "region": "us", "openness": "open",
                   "google_queries": _q("Reflection AI")},
    "minimax": {"name": "MiniMax", "tier": 2, "region": "china", "openness": "open",
                "google_queries": _q("MiniMax")},
    "tencent_hunyuan": {"name": "Tencent Hunyuan", "tier": 2, "region": "china", "openness": "open",
                        "google_queries": _q("Tencent Hunyuan", "Tencent AI model")},
    "baidu": {"name": "Baidu ERNIE", "tier": 2, "region": "china", "openness": "mixed",
              "google_queries": _q("Baidu ERNIE", "Baidu AI")},
    "stepfun": {"name": "StepFun", "tier": 2, "region": "china", "openness": "open",
                "google_queries": _q("StepFun")},
    "xiaomi_mimo": {"name": "Xiaomi MiMo", "tier": 2, "region": "china", "openness": "open",
                    "google_queries": _q("Xiaomi MiMo", "Xiaomi AI model")},
    "cohere": {"name": "Cohere", "tier": 2, "region": "other", "openness": "mixed",
               "google_queries": _q("Cohere"), "rss_feeds": _feeds("Cohere Blog")},
    "sakana": {"name": "Sakana AI", "tier": 2, "region": "other", "openness": "open",
               "google_queries": _q("Sakana AI")},
    "aleph_alpha": {"name": "Aleph Alpha", "tier": 2, "region": "europe", "openness": "open",
                    "google_queries": _q("Aleph Alpha")},
}

# The collector, classifier and weekly report still import this name; the
# module rename is part of the later clean-up that removes KDAN code.
COMPETITORS = LABS

CATEGORIES = ["model_release", "research", "product", "policy", "talent", "funding", "infra", "other"]
