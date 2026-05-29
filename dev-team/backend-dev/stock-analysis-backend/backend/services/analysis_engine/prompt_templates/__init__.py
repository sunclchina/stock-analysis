"""
M05 分析引擎 — 提示词模板包。
"""

from backend.services.analysis_engine.prompt_templates.review_template import REVIEW_SYSTEM_PROMPT, REVIEW_SYSTEM_PROMPT_SIMPLE
from backend.services.analysis_engine.prompt_templates.stock_analysis_template import (
    STOCK_ANALYSIS_SYSTEM_PROMPT,
    STOCK_ANALYSIS_SYSTEM_PROMPT_SIMPLE,
)
from backend.services.analysis_engine.prompt_templates.batch_analysis_template import (
    BATCH_ANALYSIS_SYSTEM_PROMPT,
    BATCH_ANALYSIS_SYSTEM_PROMPT_SIMPLE,
)

__all__ = [
    "REVIEW_SYSTEM_PROMPT",
    "REVIEW_SYSTEM_PROMPT_SIMPLE",
    "STOCK_ANALYSIS_SYSTEM_PROMPT",
    "STOCK_ANALYSIS_SYSTEM_PROMPT_SIMPLE",
    "BATCH_ANALYSIS_SYSTEM_PROMPT",
    "BATCH_ANALYSIS_SYSTEM_PROMPT_SIMPLE",
]
