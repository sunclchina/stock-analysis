"""
M05 分析引擎 — 盘后复盘分析。

输入日期+关注股票列表，输出结构化复盘报告。
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.services.analysis_engine.llm_client import get_llm_client
from backend.services.analysis_engine.prompt_templates import REVIEW_SYSTEM_PROMPT, REVIEW_SYSTEM_PROMPT_SIMPLE
from backend.services.analysis_engine.prompt_templates.review_template import build_review_user_prompt

logger = logging.getLogger(__name__)


async def generate_review(
    date_str: str,
    watch_stocks: List[str],
    market_data_provider: Optional[callable] = None,
    stock_data_provider: Optional[callable] = None,
    warning_data_provider: Optional[callable] = None,
    use_template: bool = True,
) -> Dict[str, Any]:
    """
    生成盘后复盘报告。

    Args:
        date_str: 复盘日期（如 "2026-04-29"）
        watch_stocks: 关注股票代码列表（≤10只）
        market_data_provider: 大盘数据获取回调
        stock_data_provider: 个股行情数据获取回调
        warning_data_provider: 预警数据获取回调

    Returns:
        {
            "date": str,
            "status": "completed" | "failed",
            "report": str (Markdown内容),
            "report_type": "review",
            "error": str | None,
        }
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 收集基础数据
    market_data = {}
    watch_stocks_data = {}
    warning_summary = {}

    if market_data_provider:
        try:
            market_data = await market_data_provider()
        except Exception as e:
            logger.warning(f"获取大盘数据失败: {e}")
            market_data = {"error": str(e)}

    if stock_data_provider and watch_stocks:
        try:
            watch_stocks_data = await stock_data_provider(watch_stocks)
        except Exception as e:
            logger.warning(f"获取个股数据失败: {e}")
            watch_stocks_data = {"error": str(e)}

    if warning_data_provider and watch_stocks:
        try:
            warning_summary = await warning_data_provider(watch_stocks)
        except Exception as e:
            logger.warning(f"获取预警数据失败: {e}")
            warning_summary = {"error": str(e)}

    # 构造关注股票信息：即使行情数据获取失败，也要传递股票代码列表
    # 确保AI始终看到用户输入的股票代码
    watch_stocks_for_prompt = {
        "input_codes": watch_stocks,
        "market_data": watch_stocks_data,
    }
    watch_stocks_text = json.dumps(watch_stocks_for_prompt, ensure_ascii=False, default=str)

    # 构建提示词
    user_prompt = build_review_user_prompt(
        date_str=date_str,
        market_data=json.dumps(market_data, ensure_ascii=False, default=str),
        watch_stocks_data=watch_stocks_text,
        warning_summary=json.dumps(warning_summary, ensure_ascii=False, default=str),
    ) 

    # 调用LLM（启用联网搜索，获取最新市场数据）
    client = get_llm_client()
    system_prompt = REVIEW_SYSTEM_PROMPT if use_template else REVIEW_SYSTEM_PROMPT_SIMPLE
    logger.info(f"复盘分析 [{date_str}]: use_template={use_template}, prompt_len={len(system_prompt)}")
    result = await client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        max_tokens=8192,
        search=True,
    )

    if result["success"]:
        logger.info(f"复盘报告生成完成 [{date_str}], 关注股票: {len(watch_stocks)}只")
        return {
            "date": date_str,
            "status": "completed",
            "report": result["content"],
            "report_type": "review",
            "watch_stocks": watch_stocks,
            "usage": result.get("usage"),
            "error": None,
        }
    else:
        logger.error(f"复盘报告生成失败 [{date_str}]: {result['error']}")
        return {
            "date": date_str,
            "status": "failed",
            "report": result["content"],
            "report_type": "review",
            "watch_stocks": watch_stocks,
            "error": result["error"],
        }
