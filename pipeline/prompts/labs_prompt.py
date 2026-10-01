"""Prompts for the frontier-lab tracker: per-item classification, daily brief and weekly report."""

COMPETITOR_CLASSIFY_PROMPT = """You track frontier AI labs for an ML engineer who follows AI agents,
LLM infrastructure and open-weight models.

Given a batch of news articles or official posts about {company_name} ({domain}), classify each one.

For each article, determine:
1. **ai_related**: Is the article about this lab's AI work (models, research, products, compute,
   people, funding or policy that affects it)? Stock-price chatter, listicles and articles that only
   mention the lab in passing are false.
2. **category**: One of:
   - model_release: a new or updated model, including benchmark results announced with it
   - product: a new feature, app, API or availability change of an existing product
   - research: a paper, technical report, research blog or result
   - open_source: open weights, open code, datasets or tools released for others to use
   - infra: compute, data centers, chips, inference speed or serving
   - partnership: a deal, integration or customer announcement with another organisation
   - funding: investment, valuation, revenue or acquisition
   - talent: hiring, departures, team or organisation changes
   - policy: safety, security, regulation or government work
   - event: livestreams, launches events, conferences, hackathons, webinars, community programmes
   - other: anything else
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


LABS_DAILY_PROMPT = """你在追蹤前沿 AI 實驗室的官方動態。以下是 {date} 各實驗室官方 X 帳號的貼文，已經過分類。
請寫「今日前沿實驗室」，用台灣繁體中文，技術名詞、模型與產品名保留英文。

格式固定：
- 依實驗室分段，段首一行 `**實驗室名**`，底下 1 到 3 點：`- 一句話說做了什麼、為什麼值得注意（[貼文](連結)）`。
- 只寫今天有實質動態的實驗室：模型、研究、產品、API、定價、政策、融資、人事。純活動宣傳、轉貼、徵才與只有一句「Learn more」的貼文略過。
- 同一件事被同一家連發多則，合成一點，連結放最重要的那則。
- 最後一行：`**今日重點**：一句話說今天最重要的一件事。`

不要開頭標題，不要寫貼文裡沒有的內容。今天沒有任何實質動態就只輸出 `今天沒有重要動態。`

## 貼文

{posts}
"""

LABS_WEEKLY_FROM_DAILY_PROMPT = """以下是 {start} 到 {end} 每天的「今日前沿實驗室」。請整理成一份 Labs 週報，
用台灣繁體中文，技術名詞、模型與產品名保留英文。

用 JSON 回覆：{{"title": "一句話概括本週前沿實驗室最重要的發展", "content": "..."}}
content 是 Markdown，依序三段：
## 本週重點
3 到 5 點，跨實驗室挑最重要的事，保留原本的貼文連結。
## 各實驗室
依實驗室分段（`**實驗室名**`），把一週內的動態合併成 1 到 4 點，同一件事只寫一次，保留連結。沒有動態的實驗室不列。
## 趨勢觀察
一段話：本週各家動作透露的共同方向，或值得留意的分歧。

不要寫每日內容裡沒有的事。

## 每日內容

{days}
"""
