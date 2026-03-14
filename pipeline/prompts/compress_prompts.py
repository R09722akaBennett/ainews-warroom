"""Prompt builders for periodic compression."""

_PERIOD_LABELS = {"weekly": "週報", "monthly": "月報", "quarterly": "季報"}

_TAGS_INSTRUCTION = """
6. 加入 tags 物件，標記這段期間的關鍵實體：
   ```json
   "tags": {
     "companies": ["openai", "anthropic", ...],
     "models": ["gpt-4o", "claude-4.6", ...],
     "topics": ["agent", "rag", "on-device-ai", ...]
   }
   ```
   - companies：英文小寫公司名
   - models：模型名稱
   - topics：核心主題關鍵詞
   - 每個分類 3-10 個，只保留最重要的"""


def build_warroom_compress_prompt(
    source_text: str, period: str, start: str, end: str
) -> str:
    """Build the prompt for KDAN-focused warroom compression."""
    label = _PERIOD_LABELS[period]
    return f"""你是 KDAN Mobile 的 AI 戰情室分析師。請將以下 {label} 期間（{start} ~ {end}）的素材壓縮成一份精簡的 {label}。

## 輸出要求
1. 用 JSON 格式回覆：{{"title": "...", "content": "...", "tags": {{...}}}}
2. title：一句話概括這段期間最重要的 AI 趨勢
3. content：用繁體中文 Markdown 格式，包含：
   - **重大事件摘要**：這段期間最重要的 3-5 件事
   - **趨勢觀察**：2-3 個在這段期間浮現或延續的趨勢
   - **KDAN 相關洞察**：對 KDAN 產品策略最相關的 1-2 個觀察
4. 全文控制在 800 字以內（{label}）
5. 重點標記：用 **粗體** 標記重要公司、模型、產品名稱
{_TAGS_INSTRUCTION}

## 素材

{source_text}"""


def build_industry_compress_prompt(
    source_text: str, period: str, start: str, end: str
) -> str:
    """Build the prompt for industry-wide compression."""
    label = _PERIOD_LABELS[period]
    return f"""你是一位 AI 產業分析師。請將以下 {label} 期間（{start} ~ {end}）的 AI 產業原始資訊整理成一份全面的產業總覽 {label}。

## 重要：這不是針對任何特定公司的分析，而是 AI 產業全貌的客觀整理。

## 輸出要求
1. 用 JSON 格式回覆：{{"title": "...", "content": "...", "tags": {{...}}}}
2. title：一句話概括這段期間 AI 產業最重要的發展
3. content：用繁體中文 Markdown 格式，包含：
   - **重大發布與公告**：這段期間最重要的產品發布、模型更新、重大公告（3-5 件）
   - **研究與技術突破**：值得關注的論文、新技術、開源專案（2-3 件）
   - **產業動態**：併購、融資、人事異動、政策法規等（2-3 件）
   - **趨勢觀察**：從這些事件中歸納出的 2-3 個產業趨勢
4. 全文控制在 1000 字以內（{label}）
5. 重點標記：用 **粗體** 標記重要公司、模型、產品名稱
{_TAGS_INSTRUCTION}
7. 保持客觀中立，不偏向任何特定公司

## 素材

{source_text}"""
