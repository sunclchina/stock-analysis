"""
财务数据获取工具。
直调东方财富 push2 API 获取实时财务指标，避免AKShare线程问题。
"""

import logging
import math
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

EM_FINANCE_FIELDS = "f12,f14,f9,f23,f8,f37,f46,f48,f57,f84,f85,f115,f167,f168"


def fetch_finance_bulk(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    批量获取股票财务指标。
    直调东方财富 push2 API，支持分页。
    返回 {code: {pe, pb, turnover_rate, revenue_growth, profit_growth, debt_ratio, eps, net_margin}}
    """
    import httpx
    import math as _mh

    url = "https://push2.eastmoney.com/api/qt/clist/get"
    base_params = {
        "pn": "1", "pz": "100", "po": "1", "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f3",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81",
        "fields": EM_FINANCE_FIELDS,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    result = {}

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, params=base_params, headers=headers)
            data = r.json()
            total = data.get("data", {}).get("total", 0) or 0
            diff = data.get("data", {}).get("diff", [])
            for item in diff:
                _extract_finance(item, result)
            pages = _mh.ceil(total / 100)
            for p in range(2, pages + 1):
                try:
                    p2 = dict(base_params, pn=str(p))
                    r2 = client.get(url, params=p2, headers=headers)
                    for item in r2.json().get("data", {}).get("diff", []):
                        _extract_finance(item, result)
                except Exception:
                    continue
        logger.info(f"财务数据: 共获取 {len(result)} 只股票")
    except Exception as e:
        logger.error(f"财务数据获取失败: {e}")

    return result


def _extract_finance(item: dict, result: dict):
    """从单条EM数据中提取财务字段"""
    code = str(item.get("f12", ""))
    if not code:
        return
    result[code] = {
        "pe": _sf(item.get("f9")),
        "pb": _sf(item.get("f23")),
        "turnover_rate": _sf(item.get("f8")),
        "revenue_growth": _sf(item.get("f46")),
        "profit_growth": _sf(item.get("f168")),
        "debt_ratio": _sf(item.get("f85")),
        "eps": _sf(item.get("f48")),
        "net_margin": _sf(item.get("f84")),
        "gross_margin": _sf(item.get("f57")),
    }


def _sf(val) -> Optional[float]:
    """安全转换浮点数"""
    if val is None:
        return None
    if val == "-":
        return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None
