"""Candidate collection settings: trimmed RSS list, labs, Jev rubric."""

# Subset of config.RSS_FEEDS. Dropped: feeds the curated daily digest already
# reads (TLDR AI, Import AI, TechCrunch AI) and general tech, security,
# policy or VC feeds that rarely carried AI news in the Sept 2026 data.
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

FRESH_HOURS = 36
CROSS_DAY_DAYS = 7
SNIPPET_CHARS = 600
TOP_FOR_DEDUP = 80
KEEP_TOP = 40

JEV_MODEL = "jev-1.13.0"  # pinned: aliases can change answers between versions
JEV_WORKERS = 12
JEV_DEADLINE_S = 120
JEV_CALL_TIMEOUT_S = 20
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
