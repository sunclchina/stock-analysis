"""
M05 分析引擎 — 个股分析。

输入股票代码，输出完整分析报告（技术面+基本面+预警+综合结论）。
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from backend.services.analysis_engine.llm_client import get_llm_client
from backend.services.analysis_engine.prompt_templates import STOCK_ANALYSIS_SYSTEM_PROMPT, STOCK_ANALYSIS_SYSTEM_PROMPT_SIMPLE
from backend.services.analysis_engine.prompt_templates.stock_analysis_template import (
    build_stock_analysis_user_prompt,
)

logger = logging.getLogger(__name__)


async def analyze_stock(
    code: str,
    market_data_provider: Optional[callable] = None,
    kline_data_provider: Optional[callable] = None,
    finance_data_provider: Optional[callable] = None,
    warning_data_provider: Optional[callable] = None,
    decision_data_provider: Optional[callable] = None,
    use_template: bool = True,
) -> Dict[str, Any]:
    """
    生成个股分析报告。

    Args:
        code: 股票代码（如 "000001"）
        market_data_provider: 实时行情获取回调
        kline_data_provider: K线数据获取回调
        finance_data_provider: 财务数据获取回调
        warning_data_provider: 预警数据获取回调
        decision_data_provider: 综合决策矩阵数据获取回调

    Returns:
        {
            "code": str,
            "name": str,
            "status": "completed" | "failed",
            "report": str (Markdown内容),
            "report_type": "stock",
            "error": str | None,
        }
    """
    # 收集基础数据
    name = ""
    market_data = {}
    kline_data = []
    finance_data = {}
    warning_data = {}
    decision_data = {}

    if market_data_provider:
        try:
            md = await market_data_provider(code)
            if md:
                market_data = md
                name = md.get("name", "")
        except Exception as e:
            logger.warning(f"获取行情数据失败 [{code}]: {e}")
            market_data = {"error": str(e)}

    if kline_data_provider:
        try:
            kline_data = await kline_data_provider(code)
        except Exception as e:
            logger.warning(f"获取K线数据失败 [{code}]: {e}")
            kline_data = {"error": str(e)}

    if finance_data_provider:
        try:
            finance_data = await finance_data_provider(code)
        except Exception as e:
            logger.warning(f"获取财务数据失败 [{code}]: {e}")
            finance_data = {"error": str(e)}

    if warning_data_provider:
        try:
            warning_data = await warning_data_provider(code)
        except Exception as e:
            logger.warning(f"获取预警数据失败 [{code}]: {e}")
            warning_data = {"error": str(e)}

    if decision_data_provider:
        try:
            decision_data = await decision_data_provider(code)
        except Exception as e:
            logger.warning(f"获取决策数据失败 [{code}]: {e}")
            decision_data = {"error": str(e)}

    # 构建提示词
    user_prompt = build_stock_analysis_user_prompt(
        code=code,
        name=name or code,
        market_data=json.dumps(market_data, ensure_ascii=False, default=str),
        kline_data=json.dumps(kline_data, ensure_ascii=False, default=str),
        finance_data=json.dumps(finance_data, ensure_ascii=False, default=str),
        warning_data=json.dumps(warning_data, ensure_ascii=False, default=str),
        decision_data=json.dumps(decision_data, ensure_ascii=False, default=str),
    )

    # 调用LLM
    client = get_llm_client()
    system_prompt = STOCK_ANALYSIS_SYSTEM_PROMPT if use_template else STOCK_ANALYSIS_SYSTEM_PROMPT_SIMPLE
    logger.info(f"个股分析 [{code}]: use_template={use_template}, prompt_len={len(system_prompt)}")
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
        logger.info(f"个股分析完成 [{code} {name}]")
        return {
            "code": code,
            "name": name,
            "status": "completed",
            "report": result["content"],
            "report_type": "stock",
            "usage": result.get("usage"),
            "error": None,
        }
    else:
        logger.error(f"个股分析失败 [{code}]: {result['error']}")
        return {
            "code": code,
            "name": name or code,
            "status": "failed",
            "report": result["content"],
            "report_type": "stock",
            "error": result["error"],
        }
