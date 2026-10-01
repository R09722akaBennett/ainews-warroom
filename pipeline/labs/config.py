"""Frontier AI labs to track: queries, feeds and display attributes.

Replaced the old company competitor list on 2026-10-01. Tier 1 labs get their own
summary in the weekly report; tier 2 labs are collected the same way but only
appear in the report's overview. region is where the lab is headquartered;
openness describes its flagship models (open weights, closed, or both).
Seeded from the organizations on the arena.ai leaderboard.

The only source is each lab's official X accounts, read by labs/x_source.py;
Google News was dropped on 2026-10-01. Official blog RSS was
dropped on 2026-10-01: only 8 of the labs had a feed, and their X accounts link
every blog post anyway. Founders and leaders post far more often than the labs
and can be added once the official accounts' daily volume is known.
Microsoft AI, Safe Superintelligence and Reflection AI were
dropped from the list on 2026-10-01; the last two mostly matched unrelated news.
"""

from __future__ import annotations






LABS: dict[str, dict] = {
    # --- Tier 1 ---------------------------------------------------------
    "openai": {"x_accounts": ['OpenAI'],
               "name": "OpenAI", "tier": 1, "region": "us", "openness": "closed"},
    "anthropic": {"x_accounts": ['AnthropicAI'],
                  "name": "Anthropic", "tier": 1, "region": "us", "openness": "closed"},
    "google_deepmind": {"x_accounts": ['GoogleDeepMind', 'GoogleAI'],
                        "name": "Google DeepMind", "tier": 1, "region": "us", "openness": "mixed"},
    "xai": {"x_accounts": ['xai'],
            "name": "xAI", "tier": 1, "region": "us", "openness": "closed"},
    "meta": {"x_accounts": ['AIatMeta'],
             "name": "Meta AI", "tier": 1, "region": "us", "openness": "mixed"},
    "thinking_machines": {"x_accounts": ['thinkymachines'],
                          "name": "Thinking Machines", "tier": 1, "region": "us", "openness": "closed"},
    "deepseek": {"x_accounts": ['deepseek_ai'],
                 "name": "DeepSeek", "tier": 1, "region": "china", "openness": "open"},
    "alibaba_qwen": {"x_accounts": ['Alibaba_Qwen'],
                     "name": "Alibaba Qwen", "tier": 1, "region": "china", "openness": "open"},
    "zhipu": {"x_accounts": ['Zai_org'],
              "name": "Zhipu (Z.ai)", "tier": 1, "region": "china", "openness": "open"},
    "moonshot": {"x_accounts": ['Kimi_Moonshot'],
                 "name": "Moonshot AI", "tier": 1, "region": "china", "openness": "open"},
    "bytedance_seed": {"x_accounts": ['ByteDanceSeed_'],
                       "name": "ByteDance Seed", "tier": 1, "region": "china", "openness": "mixed"},
    "mistral": {"x_accounts": ['MistralAI'],
                "name": "Mistral AI", "tier": 1, "region": "europe", "openness": "open"},
    # --- Tier 2 ---------------------------------------------------------
    "nvidia": {"x_accounts": ['NVIDIAAIDev'],
               "name": "NVIDIA", "tier": 2, "region": "us", "openness": "open"},
    "ai2": {"x_accounts": ['allen_ai'],
            "name": "Ai2", "tier": 2, "region": "us", "openness": "open"},
    "minimax": {"x_accounts": ['MiniMax_AI'],
                "name": "MiniMax", "tier": 2, "region": "china", "openness": "open"},
    "tencent_hunyuan": {"x_accounts": ['TencentHunyuan'],
                        "name": "Tencent Hunyuan", "tier": 2, "region": "china", "openness": "open"},
    "baidu": {"x_accounts": ['Baidu_Inc'],
              "name": "Baidu ERNIE", "tier": 2, "region": "china", "openness": "mixed"},
    "stepfun": {"x_accounts": ['StepFun_ai'],
                "name": "StepFun", "tier": 2, "region": "china", "openness": "open"},
    "xiaomi_mimo": {"x_accounts": ['XiaomiMiMo'],
                    "name": "Xiaomi MiMo", "tier": 2, "region": "china", "openness": "open"},
    "cohere": {"x_accounts": ['cohere'],
               "name": "Cohere", "tier": 2, "region": "other", "openness": "mixed"},
    "sakana": {"x_accounts": ['SakanaAILabs'],
               "name": "Sakana AI", "tier": 2, "region": "other", "openness": "open"},
    "aleph_alpha": {"x_accounts": ['Aleph__Alpha'],
                    "name": "Aleph Alpha", "tier": 2, "region": "europe", "openness": "open"},
}

CATEGORIES = ["model_release", "research", "product", "policy", "talent", "funding", "infra", "other"]
