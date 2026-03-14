"""
Prompt templates — all LLM prompts live here, separated from business logic.
"""

from prompts.agent_prompt import REPORT_SYSTEM_PROMPT, AGENT_SYSTEM_PROMPT
from prompts.compress_prompts import (
    build_warroom_compress_prompt,
    build_industry_compress_prompt,
)

__all__ = [
    "REPORT_SYSTEM_PROMPT",
    "AGENT_SYSTEM_PROMPT",
    "build_warroom_compress_prompt",
    "build_industry_compress_prompt",
]
