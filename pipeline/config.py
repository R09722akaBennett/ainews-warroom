"""
Source settings shared by the candidate collector and the lab tracker.
"""

# ---------------------------------------------------------------------------
# Hacker News
# ---------------------------------------------------------------------------

HACKERNEWS_TOP_N = 50
HACKERNEWS_AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "deepmind", "mistral", "llama", "transformer", "diffusion",
    "machine learning", "deep learning", "neural", "chatbot",
    "copilot", "agent", "rag", "fine-tuning", "embedding",
    "stable diffusion", "midjourney", "hugging face", "langchain",
    "vector database", "multimodal", "reasoning", "inference",
    "quantization", "lora", "rlhf", "alignment", "safety",
    "arxiv", "benchmark", "token", "context window", "gpu",
    "nvidia", "cuda", "tpu", "groq", "perplexity", "cursor",
    "devin", "sora", "runway", "whisper", "sam", "segment",
    "deepseek", "qwen", "phi", "mcp", "moe", "mixture of experts",
]


# ---------------------------------------------------------------------------
# RSS Feeds
# ---------------------------------------------------------------------------

RSS_FEEDS = {
    # === AI Company Blogs (primary sources) ===
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Anthropic News": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "Anthropic Research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Google Developers Blog": "https://developers.googleblog.com/feeds/posts/default?alt=rss",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Mistral AI News": "https://raw.githubusercontent.com/0xSMW/rss-feeds/main/feeds/feed_mistral_news.xml",
    "NVIDIA AI Blog": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "NVIDIA Blog": "https://blogs.nvidia.com/feed/",
    "xAI News": "https://raw.githubusercontent.com/0xSMW/rss-feeds/main/feeds/feed_xai_news.xml",
    "Meta AI Blog": "https://ai.meta.com/blog/rss/",
    "Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",
    "Apple ML Research": "https://machinelearning.apple.com/rss.xml",
    "Stability AI Blog": "https://stability.ai/blog/rss",
    "Cohere Blog": "https://cohere.com/blog/rss",

    # === AI Tools & Platforms ===
    "Cursor Blog": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_cursor.xml",
    "LangChain Blog": "https://blog.langchain.com/rss/",
    "Replicate Blog": "https://replicate.com/blog/rss",
    "Vercel Blog": "https://vercel.com/atom",
    "AWS ML Blog": "https://aws.amazon.com/blogs/machine-learning/feed/",

    # === AI Newsletters & Analysis ===
    "Import AI": "https://importai.substack.com/feed",
    "The Rundown AI": "https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml",
    "TLDR AI": "https://bullrich.dev/tldr-rss/ai.rss",
    "Interconnects": "https://www.interconnects.ai/feed",
    "Latent Space": "https://www.latent.space/feed",
    "Ahead of AI": "https://magazine.sebastianraschka.com/feed",
    "Ben's Bites": "https://bensbites.beehiiv.com/feed",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "The Gradient": "https://thegradient.pub/rss/",
    "Lil'Log (Lilian Weng)": "https://lilianweng.github.io/index.xml",

    # === Tech News (AI focused) ===
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "MIT Technology Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "TechMeme": "https://www.techmeme.com/feed.xml",
    "InfoQ AI/ML": "https://feed.infoq.com/",
    "The New Stack": "https://thenewstack.io/feed/",
    "CNBC Tech": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",

    # === AI Funding & Startups ===
    "TechCrunch Startups": "https://techcrunch.com/category/startups/feed/",
    "Crunchbase News": "https://news.crunchbase.com/feed/",

    # === VC & Strategy (AI perspective) ===
    "a16z Blog": "https://a16z.com/feed/",
    "Sequoia Blog": "https://www.sequoiacap.com/feed/",
    "Y Combinator Blog": "https://www.ycombinator.com/blog/rss/",
    "Stratechery": "https://stratechery.com/feed/",

    # === Hardware & Infrastructure ===
    "SemiAnalysis": "https://www.semianalysis.com/feed",
    "Tom's Hardware": "https://www.tomshardware.com/feeds/all",

    # === AI Policy & Regulation ===
    "Politico Tech": "https://rss.politico.com/technology.xml",

    # === AI Security ===
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "The Hacker News (Security)": "https://feeds.feedburner.com/TheHackersNews",

    # === Regional / Global AI ===
    "Tech in Asia": "https://www.techinasia.com/feed",
    "EU Startups": "https://www.eu-startups.com/feed/",
    "MIT Research": "https://news.mit.edu/rss/research",
}

# ---------------------------------------------------------------------------
# Google News (AI-focused search queries)
# ---------------------------------------------------------------------------

GOOGLE_NEWS_QUERIES = [
    # AI models, agents & tools
    '("AI model" OR "AI agent" OR "large language model" OR "generative AI" OR "AI coding") when:2d',
    # AI business & startups
    '("AI startup" OR "AI funding" OR "AI acquisition" OR "AI partnership" OR "AI revenue") when:2d',
    # AI regulation, safety & policy
    '("AI regulation" OR "AI safety" OR "AI policy" OR "AI ethics" OR "AI governance") when:3d',
    # AI infrastructure & hardware
    '("AI chip" OR "AI datacenter" OR "AI infrastructure" OR "GPU" OR "AI training") when:3d',
]

# ---------------------------------------------------------------------------
# Lobsters
# ---------------------------------------------------------------------------

LOBSTERS_AI_TAGS = ["ai", "ml"]
