"""Source settings for the candidate collector (Hacker News, RSS, Google News, Lobsters)."""

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


# Only the feeds candidates/config.RSS_FEED_NAMES reads.
RSS_FEEDS = {
    # AI Company Blogs (primary sources)
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Anthropic News": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "Anthropic Research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Google Developers Blog": "https://developers.googleblog.com/feeds/posts/default?alt=rss",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Mistral AI News": "https://raw.githubusercontent.com/0xSMW/rss-feeds/main/feeds/feed_mistral_news.xml",
    "NVIDIA AI Blog": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
    "xAI News": "https://raw.githubusercontent.com/0xSMW/rss-feeds/main/feeds/feed_xai_news.xml",
    "Meta AI Blog": "https://ai.meta.com/blog/rss/",
    "Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",
    "Apple ML Research": "https://machinelearning.apple.com/rss.xml",
    "Cohere Blog": "https://cohere.com/blog/rss",

    # AI Tools & Platforms
    "Cursor Blog": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_cursor.xml",
    "LangChain Blog": "https://blog.langchain.com/rss/",

    # AI Newsletters & Analysis
    "The Rundown AI": "https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml",
    "Interconnects": "https://www.interconnects.ai/feed",
    "Latent Space": "https://www.latent.space/feed",
    "Ahead of AI": "https://magazine.sebastianraschka.com/feed",
    "Ben's Bites": "https://bensbites.beehiiv.com/feed",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "Lil'Log (Lilian Weng)": "https://lilianweng.github.io/index.xml",

    # Tech News (AI focused)
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MIT Technology Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "TechMeme": "https://www.techmeme.com/feed.xml",
    "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",

    # Hardware & Infrastructure
    "SemiAnalysis": "https://www.semianalysis.com/feed",
}

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

LOBSTERS_AI_TAGS = ["ai", "ml"]
