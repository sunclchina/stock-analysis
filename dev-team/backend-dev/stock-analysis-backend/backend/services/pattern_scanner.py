"""
形态选股引擎 - 程序化K线形态识别。
在全市场股票池中快速扫描符合特定技术形态的股票。
不依赖AI，纯算法计算，适合批量扫描。
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


# ── SMA 计算 ─────────────────────────────────────────────

def _sma(klines: List[Dict], period: int) -> List[float]:
    """计算简单移动平均线"""
    closes = [k.get('close', 0) for k in klines]
    if len(closes) < period:
        return []
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(0)
        else:
            result.append(sum(closes[i - period + 1:i + 1]) / period)
    return result


# ── 形态检测函数 ──────────────────────────────────────────

def detect_ma_bullish(klines: List[Dict]) -> Dict[str, Any]:
    """均线多头排列：MA5 > MA10 > MA20 > MA60"""
    ma5 = _sma(klines, 5)
    ma10 = _sma(klines, 10)
    ma20 = _sma(klines, 20)
    ma60 = _sma(klines, 60)

    if not all([ma5, ma10, ma20, ma60]):
        return {"matched": False, "detail": "数据不足"}

    latest = len(ma5) - 1
    if latest < 0 or latest >= len(ma10) or latest >= len(ma20) or latest >= len(ma60):
        return {"matched": False, "detail": "数据不足"}

    if ma5[latest] > ma10[latest] > ma20[latest] > ma60[latest] > 0:
        return {"matched": True, "detail": f"MA5={ma5[latest]:.2f} > MA10={ma10[latest]:.2f} > MA20={ma20[latest]:.2f} > MA60={ma60[latest]:.2f}"}

    return {"matched": False, "detail": f"MA5={ma5[latest]:.2f} MA10={ma10[latest]:.2f} MA20={ma20[latest]:.2f} MA60={ma60[latest]:.2f}"}


def detect_golden_cross(klines: List[Dict]) -> Dict[str, Any]:
    """金叉：MA5 上穿 MA10，或 MA10 上穿 MA20"""
    ma5 = _sma(klines, 5)
    ma10 = _sma(klines, 10)
    ma20 = _sma(klines, 20)

    if len(ma5) < 2 or len(ma10) < 2:
        return {"matched": False, "detail": "数据不足"}

    latest = len(ma5) - 1
    prev = latest - 1

    # MA5上穿MA10
    if prev >= 0 and prev < len(ma10) and ma5[prev] < ma10[prev] and ma5[latest] > ma10[latest]:
        return {"matched": True, "detail": "MA5金叉MA10"}
    
    if len(ma10) >= 2 and prev < len(ma20) and ma10[prev] < ma20[prev] and ma10[latest] > ma20[latest]:
        return {"matched": True, "detail": "MA10金叉MA20"}

    return {"matched": False, "detail": "无金叉信号"}


def detect_death_cross(klines: List[Dict]) -> Dict[str, Any]:
    """死叉：MA5 下穿 MA10"""
    ma5 = _sma(klines, 5)
    ma10 = _sma(klines, 10)
    if len(ma5) < 2 or len(ma10) < 2:
        return {"matched": False, "detail": "数据不足"}
    latest = len(ma5) - 1
    prev = latest - 1
    if prev >= 0 and prev < len(ma10) and ma5[prev] > ma10[prev] and ma5[latest] < ma10[latest]:
        return {"matched": True, "detail": "MA5死叉MA10"}
    return {"matched": False, "detail": "无死叉信号"}


def detect_volume_breakout(klines: List[Dict]) -> Dict[str, Any]:
    """放量突破：成交量 > 5日均量*1.5 且 涨幅 > 3%"""
    if len(klines) < 6:
        return {"matched": False, "detail": "数据不足"}

    latest = klines[-1]
    volumes = [k.get('volume', 0) for k in klines[-6:-1]]
    avg_vol = sum(volumes) / len(volumes) if volumes else 0

    cur_vol = latest.get('volume', 0)
    change_pct = latest.get('close', 0) / max(latest.get('pre_close', latest.get('open', 1)), 0.01) - 1
    change_pct = change_pct * 100 if abs(change_pct) < 100 else latest.get('close', 0) - latest.get('open', 0)

    # 尝试从kline数据获取涨跌幅
    for prev in klines[-3:-1]:
        if prev.get('close'):
            change_pct = round((latest.get('close', 0) - prev.get('close', 0)) / prev.get('close', 0) * 100, 2)
            break

    if cur_vol > avg_vol * 1.5 and change_pct > 3:
        return {"matched": True, "detail": f"放量{cur_vol/avg_vol:.1f}倍 涨幅{change_pct:.1f}%"}
    return {"matched": False, "detail": f"量比{cur_vol/max(avg_vol,1):.1f} 涨幅{change_pct:.1f}%"}


def detect_pullback(klines: List[Dict]) -> Dict[str, Any]:
    """回踩支撑：股价从高位回调至20日/60日线附近"""
    if len(klines) < 20:
        return {"matched": False, "detail": "数据不足"}

    ma20 = _sma(klines, 20)
    ma60 = _sma(klines, 60)
    if not ma20:
        return {"matched": False, "detail": "数据不足"}

    latest_close = klines[-1].get('close', 0)
    ma20_val = ma20[-1]
    ma60_val = ma60[-1] if ma60 else 0

    # 判断是否在MA20附近（±3%）
    near_ma20 = ma20_val > 0 and abs(latest_close - ma20_val) / ma20_val < 0.03
    near_ma60 = ma60_val > 0 and abs(latest_close - ma60_val) / ma60_val < 0.03

    if near_ma20:
        return {"matched": True, "detail": f"回踩MA20({ma20_val:.2f})"}
    if near_ma60:
        return {"matched": True, "detail": f"回踩MA60({ma60_val:.2f})"}
    return {"matched": False, "detail": f"距MA20 {((latest_close-ma20_val)/ma20_val*100):.1f}%" if ma20_val else "无数据"}


def detect_macd_golden(klines: List[Dict]) -> Dict[str, Any]:
    """MACD金叉：DIF上穿DEA"""
    closes = [k.get('close', 0) for k in klines]
    if len(closes) < 26:
        return {"matched": False, "detail": "数据不足"}

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)] if len(ema12) == len(ema26) else []

    if len(dif) < 9:
        return {"matched": False, "detail": "数据不足"}

    dea = _sma_dict(dif, 9)

    if len(dif) >= 2 and len(dea) >= 2:
        if dif[-2] < dea[-2] and dif[-1] > dea[-1]:
            return {"matched": True, "detail": "MACD金叉"}
        if dif[-1] < dea[-1]:
            return {"matched": False, "detail": "MACD死叉中"}
    return {"matched": False, "detail": "MACD信号不明"}


def _ema(data: List[float], period: int) -> List[float]:
    """指数移动平均"""
    if not data:
        return []
    result = []
    multiplier = 2 / (period + 1)
    ema = data[0]
    for val in data:
        ema = (val - ema) * multiplier + ema
        result.append(ema)
    return result


def _sma_dict(data: List[float], period: int) -> List[float]:
    """简单移动平均（辅助MACD）"""
    if len(data) < period:
        return []
    result = []
    for i in range(len(data)):
        if i < period - 1:
            result.append(0)
        else:
            result.append(sum(data[i - period + 1:i + 1]) / period)
    return result


# ── 扫描器 ────────────────────────────────────────────────

PATTERN_REGISTRY = {
    "ma_bullish": {"name": "均线多头排列", "detect": detect_ma_bullish, "desc": "MA5>MA10>MA20>MA60"},
    "golden_cross": {"name": "均线金叉", "detect": detect_golden_cross, "desc": "MA5上穿MA10或MA10上穿MA20"},
    "death_cross": {"name": "均线死叉", "detect": detect_death_cross, "desc": "MA5下穿MA10（空头信号）"},
    "volume_breakout": {"name": "放量突破", "detect": detect_volume_breakout, "desc": "量>5日均量1.5倍+涨幅>3%"},
    "pullback": {"name": "回踩支撑", "detect": detect_pullback, "desc": "股价回踩MA20/MA60附近"},
    "macd_golden": {"name": "MACD金叉", "detect": detect_macd_golden, "desc": "DIF上穿DEA"},
}


async def scan_pattern(
    codes: List[str],
    pattern_key: str,
    kline_provider,
    max_stocks: int = 50,
) -> List[Dict[str, Any]]:
    """
    扫描股票池，筛选出符合指定形态的股票。

    Args:
        codes: 股票代码列表
        pattern_key: 形态名称（PATTERN_REGISTRY中的key）
        kline_provider: 异步函数，接受code参数返回K线数据列表
        max_stocks: 最大返回数量

    Returns:
        匹配的股票列表，按匹配强度排序
    """
    import asyncio

    if pattern_key not in PATTERN_REGISTRY:
        return []

    detector = PATTERN_REGISTRY[pattern_key]["detect"]
    results = []

    # 并发批次：每批 20 只同时拉 K 线
    BATCH_SIZE = 20
    for i in range(0, len(codes), BATCH_SIZE):
        if len(results) >= max_stocks:
            break

        batch = codes[i:i + BATCH_SIZE]
        # 并发拉取 K 线
        kline_tasks = [kline_provider(code) for code in batch]
        kline_results = await asyncio.gather(*kline_tasks, return_exceptions=True)

        for code, klines in zip(batch, kline_results):
            if isinstance(klines, Exception) or not klines or len(klines) < 20:
                continue

            try:
                match = detector(klines)
                if match.get("matched"):
                    price = klines[-1].get('close', 0)
                    volume = klines[-1].get('volume', 0)
                    change_pct = 0
                    if len(klines) >= 2:
                        prev_close = klines[-2].get('close', 0)
                        if prev_close:
                            change_pct = round((price - prev_close) / prev_close * 100, 2)

                    results.append({
                        "code": code,
                        "name": "",
                        "price": price,
                        "change_pct": change_pct,
                        "volume": volume,
                        "pattern_detail": match.get("detail", ""),
                    })

                    if len(results) >= max_stocks:
                        break
            except Exception:
                continue

    return results
