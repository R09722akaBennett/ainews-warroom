"""Candidate collection settings: trimmed RSS list, freshness, Jev limits and answer choices."""

# The feeds to read; config.RSS_FEEDS holds their URLs. Left out: feeds the
# curated daily digest already reads (TLDR AI, Import AI, TechCrunch AI) and
# general tech, security, policy or VC feeds that rarely carried AI news in
# the September 2026 data.
RSS_FEED_NAMES = [
    "OpenAI Blog", "Anthropic News", "Anthropic Research", "Google AI Blog",
    "Google DeepMind", "Google Developers Blog", "Hugging Face Blog",
    "Mistral AI News", "NVIDIA AI Blog", "xAI News", "Meta AI Blog",
    "Microsoft AI Blog", "Apple ML Research", "Cohere Blog",
    "Cursor Blog", "LangChain Blog",
    "Interconnects", "Latent Space", "Ahead of AI", "Simon Willison",
    "Lil'Log (Lilian Weng)", "The Rundown AI", "Ben's Bites",
    "VentureBeat AI", "The Verge AI", "MIT Technology Review AI", "TechMeme",
    "Wired AI", "SemiAnalysis",
]

# Longer than the 24 h between runs, so an item a feed dates late or posts
# just before a run is not lost; the cross-day URL check drops the overlap.
# No recorded reason for 36 exactly; chosen by trial.
FRESH_HOURS = 36
CROSS_DAY_DAYS = 7
SNIPPET_CHARS = 600
# Each same-event check costs one Jev call per item, so only the top of the
# ranking is checked; the digest takes at most its top 15 at 0.75 or more.
# No recorded reason for 80; chosen by trial.
TOP_FOR_DEDUP = 80

JEV_MODEL = "jev-1.13.0"  # pinned: aliases can change answers between versions
# No recorded reason for 12 workers; chosen by trial.
JEV_WORKERS = 12
# The whole Jev stage must finish well before the 18:00 digest reads the file
# (the job starts at 17:35); calls still running at the deadline count as
# failures. No recorded reason for 120 s; chosen by trial.
JEV_DEADLINE_S = 120
JEV_CALL_TIMEOUT_S = 20
# Above this share of failed calls the run is marked degraded. No recorded
# reason for 10 %; chosen by trial.
JEV_MAX_FAILURE_RATE = 0.10

LABS = {
    "openai": "OpenAI, ChatGPT, GPT models, Codex",
    "anthropic": "Anthropic, Claude",
    "google_deepmind": "Google DeepMind, Google AI, Gemini",
    "meta": "Meta AI, Llama, Muse",
    "xai": "xAI, Grok",
    "thinking_machines": "Thinking Machines Lab",
    "deepseek": "DeepSeek",
    "alibaba_qwen": "Alibaba, Qwen",
    "zhipu": "Zhipu, GLM, Z.ai",
    "moonshot": "Moonshot AI, Kimi",
    "bytedance_seed": "ByteDance, Seed, Doubao",
    "mistral": "Mistral AI",
    "microsoft_ai": "Microsoft AI, Copilot models",
    "nvidia": "NVIDIA models and research (Nemotron, Cosmos)",
    "minimax": "MiniMax",
    "other_lab": "Another AI lab or model company not listed",
    "none": "No AI lab is the primary subject",
}

CATEGORIES = {
    "model_release": "A new model or model version is announced or shipped",
    "research": "A paper, technical report or research finding",
    "product": "A product, feature, API or app launch",
    "policy": "Regulation, government action, safety policy or a legal case",
    "talent": "Hiring, departures or leadership changes of named people",
    "funding": "Investment, valuation, acquisition or revenue",
    "infra": "Chips, data centers, compute deals, serving or training infrastructure",
    "other": "None of the above",
}
