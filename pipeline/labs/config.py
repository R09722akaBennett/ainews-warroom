"""Frontier AI labs to track: queries, feeds and display attributes.

Replaced the old company competitor list on 2026-10-01. Tier 1 labs get their own
summary in the weekly report; tier 2 labs are collected the same way but only
appear in the report's overview. region is where the lab is headquartered;
openness describes its flagship models (open weights, closed, or both).
Seeded from the organizations on the arena.ai leaderboard.

Sources per lab are Google News (press coverage: funding, people, policy) and
the lab's official X accounts, read by labs/x_source.py. Official blog RSS was
dropped on 2026-10-01: only 8 of the labs had a feed, and their X accounts link
every blog post anyway. Founders and leaders post far more often than the labs
and can be added once the official accounts' daily volume is known. SSI has no
official account. Microsoft AI was dropped from the list on 2026-10-01.
"""

from __future__ import annotations



def _q(*names: str, extra: str = "AI OR model OR LLM") -> list[str]:
    alts = " OR ".join(f'"{n}"' for n in names)
    return [f"({alts}) ({extra}) when:3d"]



LABS: dict[str, dict] = {
    # --- Tier 1 ---------------------------------------------------------
    "openai": {"x_accounts": ['OpenAI'],
               "name": "OpenAI", "tier": 1, "region": "us", "openness": "closed",
               "google_queries": _q("OpenAI")},
    "anthropic": {"x_accounts": ['AnthropicAI'],
                  "name": "Anthropic", "tier": 1, "region": "us", "openness": "closed",
                  "google_queries": _q("Anthropic")},
    "google_deepmind": {"x_accounts": ['GoogleDeepMind', 'GoogleAI'],
                        "name": "Google DeepMind", "tier": 1, "region": "us", "openness": "mixed",
                        "google_queries": _q("Google DeepMind", "Gemini model")},
    "xai": {"x_accounts": ['xai'],
            "name": "xAI", "tier": 1, "region": "us", "openness": "closed",
            "google_queries": _q("xAI", "Grok")},
    "meta": {"x_accounts": ['AIatMeta'],
             "name": "Meta AI", "tier": 1, "region": "us", "openness": "mixed",
             "google_queries": _q("Meta AI", "Meta Superintelligence", "Llama model")},
    "thinking_machines": {"x_accounts": ['thinkymachines'],
                          "name": "Thinking Machines", "tier": 1, "region": "us", "openness": "closed",
                          "google_queries": _q("Thinking Machines Lab", "Mira Murati", extra="AI OR startup OR model")},
    "deepseek": {"x_accounts": ['deepseek_ai'],
                 "name": "DeepSeek", "tier": 1, "region": "china", "openness": "open",
                 "google_queries": _q("DeepSeek")},
    "alibaba_qwen": {"x_accounts": ['Alibaba_Qwen'],
                     "name": "Alibaba Qwen", "tier": 1, "region": "china", "openness": "open",
                     "google_queries": _q("Qwen", "Alibaba Cloud AI", "Tongyi")},
    "zhipu": {"x_accounts": ['Zai_org'],
              "name": "Zhipu (Z.ai)", "tier": 1, "region": "china", "openness": "open",
              "google_queries": _q("Zhipu", "Z.ai", "GLM model")},
    "moonshot": {"x_accounts": ['Kimi_Moonshot'],
                 "name": "Moonshot AI", "tier": 1, "region": "china", "openness": "open",
                 "google_queries": _q("Moonshot AI", "Kimi")},
    "bytedance_seed": {"x_accounts": ['ByteDanceSeed_'],
                       "name": "ByteDance Seed", "tier": 1, "region": "china", "openness": "mixed",
                       "google_queries": _q("ByteDance Seed", "Doubao", "ByteDance AI")},
    "mistral": {"x_accounts": ['MistralAI'],
                "name": "Mistral AI", "tier": 1, "region": "europe", "openness": "open",
                "google_queries": _q("Mistral AI")},
    # --- Tier 2 ---------------------------------------------------------
    "nvidia": {"x_accounts": ['NVIDIAAIDev'],
               "name": "NVIDIA", "tier": 2, "region": "us", "openness": "open",
               "google_queries": _q("Nvidia Nemotron", "Nvidia AI model")},
    "ai2": {"x_accounts": ['allen_ai'],
            "name": "Ai2", "tier": 2, "region": "us", "openness": "open",
            "google_queries": _q("Allen Institute for AI", "Ai2 OLMo")},
    "ssi": {"name": "Safe Superintelligence", "tier": 2, "region": "us", "openness": "closed",
            "google_queries": _q("Safe Superintelligence", "Ilya Sutskever", extra="AI OR startup")},
    "reflection": {"x_accounts": ['reflection_ai'],
                   "name": "Reflection AI", "tier": 2, "region": "us", "openness": "open",
                   "google_queries": _q("Reflection AI")},
    "minimax": {"x_accounts": ['MiniMax__AI'],
                "name": "MiniMax", "tier": 2, "region": "china", "openness": "open",
                "google_queries": _q("MiniMax")},
    "tencent_hunyuan": {"x_accounts": ['TencentHunyuan'],
                        "name": "Tencent Hunyuan", "tier": 2, "region": "china", "openness": "open",
                        "google_queries": _q("Tencent Hunyuan", "Tencent AI model")},
    "baidu": {"x_accounts": ['Baidu_Inc'],
              "name": "Baidu ERNIE", "tier": 2, "region": "china", "openness": "mixed",
              "google_queries": _q("Baidu ERNIE", "Baidu AI")},
    "stepfun": {"x_accounts": ['StepFun_ai'],
                "name": "StepFun", "tier": 2, "region": "china", "openness": "open",
                "google_queries": _q("StepFun")},
    "xiaomi_mimo": {"x_accounts": ['XiaomiMiMo'],
                    "name": "Xiaomi MiMo", "tier": 2, "region": "china", "openness": "open",
                    "google_queries": _q("Xiaomi MiMo", "Xiaomi AI model")},
    "cohere": {"x_accounts": ['cohere'],
               "name": "Cohere", "tier": 2, "region": "other", "openness": "mixed",
               "google_queries": _q("Cohere")},
    "sakana": {"x_accounts": ['SakanaAILabs'],
               "name": "Sakana AI", "tier": 2, "region": "other", "openness": "open",
               "google_queries": _q("Sakana AI")},
    "aleph_alpha": {"x_accounts": ['Aleph__Alpha'],
                    "name": "Aleph Alpha", "tier": 2, "region": "europe", "openness": "open",
                    "google_queries": _q("Aleph Alpha")},
}

CATEGORIES = ["model_release", "research", "product", "policy", "talent", "funding", "infra", "other"]
