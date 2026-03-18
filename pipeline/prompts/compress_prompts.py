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


def _build_previous_context(previous_summary: dict | None, label: str) -> str:
    """Build the previous period context section."""
    if not previous_summary:
        return ""
    return f"""

## 上一期{label}（{previous_summary['start_date']} ~ {previous_summary['end_date']}）

以下是上一期的摘要，請參考以識別跨期趨勢的演變脈絡：

{previous_summary['content']}
"""


def build_warroom_compress_prompt(
    source_text: str, period: str, start: str, end: str,
    previous_summary: dict | None = None,
) -> str:
    """Build the prompt for KDAN-focused warroom compression."""
    label = _PERIOD_LABELS[period]
    prev_context = _build_previous_context(previous_summary, label)
    return f"""你是 KDAN Mobile 的 AI 戰情室分析師。請將以下 {label} 期間（{start} ~ {end}）的素材整理成一份完整的 {label}。

## 輸出要求
1. 用 JSON 格式回覆：{{"title": "...", "content": "...", "tags": {{...}}}}
2. title：一句話概括這段期間最重要的 AI 趨勢
3. content：用繁體中文 Markdown 格式，包含：
   - **重大事件摘要**：這段期間最重要的事件，保留具體數字、金額、日期等關鍵數據
   - **趨勢觀察**：在這段期間浮現的趨勢，並與上一期脈絡對照說明其演變
   - **KDAN 相關洞察**：對 KDAN 產品策略最相關的觀察與具體建議
4. 這是一份{label}，以完整性與品質為優先，不需刻意縮減篇幅
5. 重點標記：用 **粗體** 標記重要公司、模型、產品名稱
{_TAGS_INSTRUCTION}
{prev_context}
## 本期素材

{source_text}"""


def build_industry_compress_prompt(
    source_text: str, period: str, start: str, end: str,
    previous_summary: dict | None = None,
) -> str:
    """Build the prompt for industry-wide compression."""
    label = _PERIOD_LABELS[period]
    prev_context = _build_previous_context(previous_summary, label)
    return f"""你是一位 AI 產業分析師。請將以下 {label} 期間（{start} ~ {end}）的 AI 產業原始資訊整理成一份全面的產業總覽 {label}。

## 重要：這不是針對任何特定公司的分析，而是 AI 產業全貌的客觀整理。

## 輸出要求
1. 用 JSON 格式回覆：{{"title": "...", "content": "...", "tags": {{...}}}}
2. title：一句話概括這段期間 AI 產業最重要的發展
3. content：用繁體中文 Markdown 格式，包含：
   - **重大發布與公告**：這段期間最重要的產品發布、模型更新、重大公告，保留具體數字與日期
   - **研究與技術突破**：值得關注的論文、新技術、開源專案
   - **產業動態**：併購、融資、人事異動、政策法規等
   - **趨勢觀察**：從這些事件中歸納出的產業趨勢，並與上一期脈絡對照說明其演變
4. 這是一份{label}，以完整性與品質為優先，不需刻意縮減篇幅
5. 重點標記：用 **粗體** 標記重要公司、模型、產品名稱
{_TAGS_INSTRUCTION}
7. 保持客觀中立，不偏向任何特定公司
{prev_context}
## 本期素材

{source_text}"""
