"""Prompts for the frontier-lab tracker: per-item classification and weekly report."""

COMPETITOR_CLASSIFY_PROMPT = """You track frontier AI labs for an ML engineer who follows AI agents,
LLM infrastructure and open-weight models.

Given a batch of news articles about {company_name} ({domain}), classify each one.

For each article, determine:
1. **ai_related**: Is the article about this lab's AI work (models, research, products, compute,
   people, funding or policy that affects it)? Stock-price chatter, listicles and articles that only
   mention the lab in passing are false.
2. **category**: One of: model_release, research, product, policy, talent, funding, infra, other
3. **summary**: One sentence in Traditional Chinese (Taiwan), keeping product and company names in
   English, saying what happened and why it matters.

Return a JSON array in the same order as the input articles:
```json
[
  {{"index": 0, "ai_related": true, "category": "model_release", "summary": "Anthropic 發表 Claude Sonnet 5.5，程式與代理任務表現接近 Opus。"}},
  {{"index": 1, "ai_related": false, "category": "other", "summary": "股價評論，與 AI 進展無關。"}}
]
```

Only return the JSON array, no other text.

## Articles about {company_name}

{articles_text}
"""


COMPETITOR_WEEKLY_PROMPT = """你是前沿 AI 實驗室動態的分析師，讀者是關注 AI agent、LLM 基礎設施與開源模型的 ML 工程師。
根據以下過去一週各實驗室的動態，產出一份實驗室週報。

## 輸出要求

用 JSON 格式回覆：
```json
{{
  "title": "實驗室週報標題（一句話點出本週主軸）",
  "content": "完整 Markdown 週報",
  "tags": {{
    "companies": ["openai", "deepseek"],
    "categories": ["model_release", "funding"],
    "topics": ["agents", "open-weights"]
  }}
}}
```

### content 格式

#### 本週重點
- 3-5 條最重要的動態，每條 2-3 句，說明為什麼重要
- 引用新聞時**必須**使用 `(ref-N)` 格式，保留原文中的 ref 編號

#### 各實驗室
每家有動態的 Tier 1 實驗室一個小節：名稱、地區與開閉源、本週動態列表（每條附 ref 編號）

#### 其他實驗室
Tier 2 實驗室的動態合併成一個列表，每條一句並附 ref 編號

#### 格局觀察
2-3 條跨實驗室的觀察，例如美中開源與閉源的消長、算力與資金流向、人才移動，引用相關 ref

## 重要原則
- 跳過無關緊要的內容（一般性部落格、SEO 文章、股價評論）
- **所有引用必須使用 ref-N 格式**，保留來源的 ref 編號不要改動
- 使用台灣繁體中文，公司、模型與產品名稱保留英文

## 本週實驗室新聞

{news_text}
"""
