"""
M05 分析引擎 — 批量分析。

输入股票列表（≤10只），逐只分析+汇总对比。
"""

import json
import logging
from typing import List, Optional, Dict, Any

from backend.services.analysis_engine.llm_client import get_llm_client
from backend.services.analysis_engine.prompt_templates import BATCH_ANALYSIS_SYSTEM_PROMPT, BATCH_ANALYSIS_SYSTEM_PROMPT_SIMPLE
from backend.services.analysis_engine.prompt_templates.batch_analysis_template import (
    build_batch_analysis_user_prompt,
)

logger = logging.getLogger(__name__)


async def batch_analyze(
    codes: List[str],
    stock_data_provider: Optional[callable] = None,
    warning_data_provider: Optional[callable] = None,
    use_template: bool = True,
) -> Dict[str, Any]:
    """
    批量分析多只股票。

    Args:
        codes: 股票代码列表（≤10只）
        stock_data_provider: 批量获取股票完整数据的回调
        warning_data_provider: 预警数据获取回调

    Returns:
        {
            "codes": [...],
            "status": "completed" | "failed",
            "report": str (Markdown内容),
            "report_type": "batch",
            "items_analyzed": int,
            "error": str | None,
        }
    """
    if len(codes) > 10:
        codes = codes[:10]
        logger.warning(f"批量分析最多10只，已截断为前10只")

    if not codes:
        return {
            "codes": [],
            "status": "failed",
            "report": "# ⚠️ 输入为空\n\n请提供至少一只股票的代码。",
            "report_type": "batch",
            "items_analyzed": 0,
            "error": "股票列表为空",
        }

    # 收集数据
    stocks_data = {}
    warning_summary = {}

    if stock_data_provider:
        try:
            stocks_data = await stock_data_provider(codes)
        except Exception as e:
            logger.warning(f"获取批量数据失败: {e}")
            stocks_data = {"error": str(e)}

    if warning_data_provider and codes:
        try:
            warning_summary = await warning_data_provider(codes)
        except Exception as e:
            logger.warning(f"获取预警数据失败: {e}")
            warning_summary = {"error": str(e)}

    # 构建提示词
    user_prompt = build_batch_analysis_user_prompt(
        stocks_data=json.dumps(stocks_data, ensure_ascii=False, default=str),
        warning_data=json.dumps(warning_summary, ensure_ascii=False, default=str),
    )

    # 调用LLM
    client = get_llm_client()
    system_prompt = BATCH_ANALYSIS_SYSTEM_PROMPT if use_template else BATCH_ANALYSIS_SYSTEM_PROMPT_SIMPLE
    logger.info(f"批量分析: use_template={use_template}, prompt_len={len(system_prompt)}")
    result = await client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=8192,
        search=True,
    )

    if result["success"]:
        logger.info(f"批量分析完成: {len(codes)}只股票")
        return {
            "codes": codes,
            "status": "completed",
            "report": result["content"],
            "report_type": "batch",
            "items_analyzed": len(codes),
            "usage": result.get("usage"),
            "error": None,
        }
    else:
        logger.error(f"批量分析失败 ({len(codes)}只): {result['error']}")
        return {
            "codes": codes,
            "status": "failed",
            "report": result["content"],
            "report_type": "batch",
            "items_analyzed": 0,
            "error": result["error"],
        }
