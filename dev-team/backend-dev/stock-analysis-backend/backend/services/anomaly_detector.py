"""
交易异动检测服务。

根据实时行情 + K线数据，检测个股是否触发各种交易异动。
利好异动🟢、利空异动🔴，供前端"实时行情"列表展示。

数据来源：实时行情(QuoteData)、日K线(KLineData)
部分异动（大单/封单/竞价等）需要更深层数据，标注为"需Level2"。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date

from backend.services.data_source.base import QuoteData, KLineData

logger = logging.getLogger(__name__)

# ── 异动定义 ──

ANOMALY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # 🟢 利好
    "rocket_launch": {
        "name": "火箭发射",
        "type": "bullish",
        "desc": "短时间涨幅≥3%且放量",
        "needs_intraday": True,
    },
    "quick_rebound": {
        "name": "快速反弹",
        "type": "bullish",
        "desc": "从日内低点回升≥2%且放量",
        "needs_intraday": True,
    },
    "big_buy": {
        "name": "大笔买入",
        "type": "bullish",
        "desc": "大单买入金额/占比达阈值",
        "needs_level2": True,
    },
    "limit_up": {
        "name": "封涨停板",
        "type": "bullish",
        "desc": "触及涨停价且买一有大额封单",
        "needs_level2": True,
    },
    "open_limit_down": {
        "name": "打开跌停板",
        "type": "bullish",
        "desc": "从跌停价打开且放量",
        "needs_intraday": True,
    },
    "big_buy_orders": {
        "name": "有大买盘",
        "type": "bullish",
        "desc": "买一/买二挂单远大于卖盘",
        "needs_level2": True,
    },
    "auction_up": {
        "name": "竞价上涨",
        "type": "bullish",
        "desc": "集合竞价涨幅≥1%且量比放大",
        "needs_premarket": True,
    },
    "gap_up_5ma": {
        "name": "高开5日线",
        "type": "bullish",
        "desc": "开盘价高于5日均线且高开≥1%",
    },
    "upward_gap": {
        "name": "向上缺口",
        "type": "bullish",
        "desc": "今日最低>昨日最高，跳空缺口",
    },
    "new_60d_high": {
        "name": "60日新高",
        "type": "bullish",
        "desc": "价格创近60日最高",
    },
    "surge_60d": {
        "name": "60日大幅上涨",
        "type": "bullish",
        "desc": "近60日涨幅≥30%",
    },
    "open_limit_up": {
        "name": "打开涨停板",
        "type": "neutral",
        "desc": "从涨停价打开，放量，关注回封",
        "needs_intraday": True,
    },
    # 🔴 利空
    "accelerate_down": {
        "name": "加速下跌",
        "type": "bearish",
        "desc": "短时间跌幅≥3%且放量",
        "needs_intraday": True,
    },
    "cliff_drop": {
        "name": "高台跳水",
        "type": "bearish",
        "desc": "从日内高点快速回落≥3%",
        "needs_intraday": True,
    },
    "big_sell": {
        "name": "大笔卖出",
        "type": "bearish",
        "desc": "大单卖出金额/占比达阈值",
        "needs_level2": True,
    },
    "limit_down": {
        "name": "封跌停板",
        "type": "bearish",
        "desc": "触及跌停价且卖一有大额封单",
        "needs_level2": True,
    },
    "big_sell_orders": {
        "name": "有大卖盘",
        "type": "bearish",
        "desc": "卖一/卖二挂单远大于买盘",
        "needs_level2": True,
    },
    "auction_down": {
        "name": "竞价下跌",
        "type": "bearish",
        "desc": "集合竞价跌幅≥1%且量比放大",
        "needs_premarket": True,
    },
    "gap_down_5ma": {
        "name": "低开5日线",
        "type": "bearish",
        "desc": "开盘价低于5日均线且低开≥1%",
    },
    "downward_gap": {
        "name": "向下缺口",
        "type": "bearish",
        "desc": "今日最高<昨日最低，跳空缺口",
    },
    "new_60d_low": {
        "name": "60日新低",
        "type": "bearish",
        "desc": "价格创近60日最低",
    },
    "plunge_60d": {
        "name": "60日大幅下跌",
        "type": "bearish",
        "desc": "近60日跌幅≥20%",
    },
}

# 需要K线数据才能检测的异动ID
_KLINE_REQUIRED = {
    "gap_up_5ma", "upward_gap", "new_60d_high", "surge_60d",
    "gap_down_5ma", "downward_gap", "new_60d_low", "plunge_60d",
}


def detect_anomalies(
    code: str,
    price: float,
    change_pct: float,
    open_price: float,
    high: float,
    low: float,
    pre_close: float,
    volume: float,
    amount: float,
    closes: Optional[List[float]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    volumes: Optional[List[float]] = None,
    trade_dates: Optional[List] = None,
) -> List[Dict[str, Any]]:
    """
    检测单只股票的所有交易异动。

    Args:
        code: 股票代码
        price: 当前最新价
        change_pct: 涨跌幅(%)
        open_price: 开盘价
        high: 当日最高
        low: 当日最低
        pre_close: 昨收
        volume: 成交量
        amount: 成交额
        closes: 近60日收盘价序列（最新在最后）
        highs: 近60日最高价序列
        lows: 近60日最低价序列
        volumes: 近60日成交量序列
        trade_dates: 交易日序列

    Returns:
        list[dict]: 触发的异动列表，每个含 id/name/type
    """
    triggered: List[Dict[str, Any]] = []

    # ── 无需K线即可检测的异动 ──
    _check_limit(triggered, code, price, pre_close, change_pct, volume, amount, high, low)

    # ── 需要K线数据的异动 ──
    if closes and len(closes) >= 5:
        _check_kline_anomalies(triggered, code, price, change_pct, open_price,
                               high, low, pre_close, volume, closes, highs, lows, volumes)

    return triggered


def _check_limit(triggered: List, code: str, price: float, pre_close: float,
                  change_pct: float, volume: float, amount: float,
                  high: float = 0, low: float = 0):
    """检测无需K线的异动（涨跌停相关）"""
    if pre_close <= 0:
        return

    limit_up_price = round(pre_close * 1.10, 2)  # 10%涨停
    limit_down_price = round(pre_close * 0.90, 2)

    # 封涨停板（价格触及涨停）
    if price >= limit_up_price and change_pct >= 9.5:
        triggered.append({
            "id": "limit_up",
            "name": "封涨停板",
            "type": "bullish",
        })

    # 封跌停板（价格触及跌停）
    if price <= limit_down_price and change_pct <= -9.5:
        triggered.append({
            "id": "limit_down",
            "name": "封跌停板",
            "type": "bearish",
        })

    # 火箭发射（涨幅≥3% 且需放量，用振幅辅助判断）
    if change_pct >= 3.0:
        triggered.append({
            "id": "rocket_launch",
            "name": "火箭发射",
            "type": "bullish",
        })

    # 加速下跌（跌幅≥3%）
    if change_pct <= -3.0:
        triggered.append({
            "id": "accelerate_down",
            "name": "加速下跌",
            "type": "bearish",
        })

    # 高台跳水（从高点回落≥3% - 用振幅辅助）
    # 通过振幅粗略判断：如果振幅≥4%且收盘在低位，可能属于高台跳水
    high_to_close = (high - price) / (high if high > 0 else 1) * 100
    if high_to_close >= 3.0 and change_pct < 0:
        triggered.append({
            "id": "cliff_drop",
            "name": "高台跳水",
            "type": "bearish",
        })


def _check_kline_anomalies(triggered: List, code: str, price: float, change_pct: float,
                             open_price: float, high: float, low: float, pre_close: float,
                             volume: float, closes: List[float], highs: List[float],
                             lows: List[float], volumes: List[float]):
    """检测需要K线数据的异动"""
    n = len(closes)

    # ── 计算均线 ──
    ma5 = sum(closes[-5:]) / 5 if n >= 5 else 0

    # ── 昨日数据 ──
    yesterday_close = closes[-2] if n >= 2 else pre_close
    yesterday_high = highs[-2] if highs and len(highs) >= 2 else 0
    yesterday_low = lows[-2] if lows and len(lows) >= 2 else 0

    # 高开5日线 / 低开5日线
    if ma5 > 0 and open_price > 0:
        gap_to_ma5 = (open_price / ma5 - 1) * 100
        if gap_to_ma5 >= 1.0:
            triggered.append({
                "id": "gap_up_5ma",
                "name": "高开5日线",
                "type": "bullish",
            })
        elif gap_to_ma5 <= -1.0:
            triggered.append({
                "id": "gap_down_5ma",
                "name": "低开5日线",
                "type": "bearish",
            })

    # 向上缺口 / 向下缺口
    if yesterday_high > 0 and yesterday_low > 0:
        if low > yesterday_high:
            triggered.append({
                "id": "upward_gap",
                "name": "向上缺口",
                "type": "bullish",
            })
        elif high < yesterday_low:
            triggered.append({
                "id": "downward_gap",
                "name": "向下缺口",
                "type": "bearish",
            })

    # 60日新高 / 60日新低
    if highs and len(highs) >= 5:
        d_high = max(highs[-min(60, len(highs)):])
        d_low = min(lows[-min(60, len(lows)):])
        if price >= d_high:
            triggered.append({
                "id": "new_60d_high",
                "name": "60日新高",
                "type": "bullish",
            })
        if price <= d_low:
            triggered.append({
                "id": "new_60d_low",
                "name": "60日新低",
                "type": "bearish",
            })

    # 60日大幅上涨 / 大幅下跌
    if n >= 10:
        past_close = closes[0]
        if past_close > 0:
            change_60d = (closes[-1] / past_close - 1) * 100
            if change_60d >= 30:
                triggered.append({
                    "id": "surge_60d",
                    "name": "60日大幅上涨",
                    "type": "bullish",
                })
            elif change_60d <= -20:
                triggered.append({
                    "id": "plunge_60d",
                    "name": "60日大幅下跌",
                    "type": "bearish",
                })

    # 打开跌停板（从跌停打开且放量）
    # 条件：昨日收盘价的-9.5%以下有记录，且当前价格已回升
    threshold = round(yesterday_close * 0.905, 2) if yesterday_close > 0 else 0
    if threshold > 0 and low <= threshold and price > threshold and volumes and len(volumes) >= 2:
        prev_vol = volumes[-2] if volumes[-2] > 0 else volume
        vol_ratio = volume / prev_vol if prev_vol > 0 else 1
        if vol_ratio >= 1.3:
            triggered.append({
                "id": "open_limit_down",
                "name": "打开跌停板",
                "type": "bullish",
            })

    # 打开涨停板（从涨停打开且放量）
    limit_up_threshold = round(yesterday_close * 1.095, 2) if yesterday_close > 0 else 0
    if limit_up_threshold > 0 and high >= limit_up_threshold and price < limit_up_threshold:
        if volumes and len(volumes) >= 2:
            prev_vol = volumes[-2] if volumes[-2] > 0 else volume
            vol_ratio = volume / prev_vol if prev_vol > 0 else 1
            if vol_ratio >= 1.3:
                triggered.append({
                    "id": "open_limit_up",
                    "name": "打开涨停板",
                    "type": "neutral",
                })

    # 快速反弹（用变化率和振幅判断）
    amplitude = (high - low) / (low if low > 0 else 1) * 100
    if amplitude >= 4.0 and change_pct > 0:
        triggered.append({
            "id": "quick_rebound",
            "name": "快速反弹",
            "type": "bullish",
        })


async def batch_detect_anomalies(
    quotes: List[QuoteData],
    dsm,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    批量检测多只股票的交易异动。

    Args:
        quotes: 行情数据列表
        dsm: 数据源管理器

    Returns:
        dict: { code: [anomaly, ...] }
    """
    import asyncio
    from backend.services.data_source.fallback import DataSourceManager

    result: Dict[str, List[Dict[str, Any]]] = {}

    # 收集需要获取K线的股票
    kline_tasks = []
    for q in quotes:
        code = q.code if hasattr(q, 'code') else (q.get('code', '') if isinstance(q, dict) else '')
        if code:
            kline_tasks.append(_fetch_kline_for_anomaly(code, dsm))

    # 并发获取K线
    kline_results = await asyncio.gather(*kline_tasks, return_exceptions=True)

    for q in quotes:
        code = q.code if hasattr(q, 'code') else (q.get('code', '') if isinstance(q, dict) else '')
        if not code:
            continue

        price = q.price if hasattr(q, 'price') else (q.get('price', 0) if isinstance(q, dict) else 0)
        change_pct = q.change_pct if hasattr(q, 'change_pct') else (q.get('change_pct', 0) if isinstance(q, dict) else 0)
        open_price = q.open_price if hasattr(q, 'open_price') else (q.get('open_price', q.get('open', 0)) if isinstance(q, dict) else 0)
        high = q.high_price if hasattr(q, 'high_price') else (q.get('high_price', q.get('high', 0)) if isinstance(q, dict) else 0)
        low = q.low_price if hasattr(q, 'low_price') else (q.get('low_price', q.get('low', 0)) if isinstance(q, dict) else 0)
        pre_close = q.pre_close if hasattr(q, 'pre_close') else (q.get('pre_close', q.get('prevClose', 0)) if isinstance(q, dict) else 0)
        volume = q.volume if hasattr(q, 'volume') else (q.get('volume', 0) if isinstance(q, dict) else 0)
        amount = q.amount if hasattr(q, 'amount') else (q.get('amount', 0) if isinstance(q, dict) else 0)

        closes, highs, lows, volumes = None, None, None, None

        # 匹配K线结果
        for kline_result in kline_results:
            if isinstance(kline_result, Exception):
                continue
            if isinstance(kline_result, dict) and kline_result.get('code') == code:
                closes = kline_result.get('closes')
                highs = kline_result.get('highs')
                lows = kline_result.get('lows')
                volumes = kline_result.get('volumes')
                break

        anomalies = detect_anomalies(
            code=code, price=price, change_pct=change_pct,
            open_price=open_price, high=high, low=low,
            pre_close=pre_close, volume=volume, amount=amount,
            closes=closes, highs=highs, lows=lows, volumes=volumes,
        )
        if anomalies:
            result[code] = anomalies

    return result


async def _fetch_kline_for_anomaly(code: str, dsm) -> Optional[Dict]:
    """获取单只股票K线数据用于异动检测"""
    try:
        from backend.services.data_source.base import KLineData
        klines = await dsm.get_kline(code, count=60)
        if not klines:
            return {"code": code, "closes": [], "highs": [], "lows": [], "volumes": []}

        closes = [k.close_price for k in klines]
        highs = [k.high_price for k in klines]
        lows = [k.low_price for k in klines]
        volumes = [k.volume for k in klines]

        return {
            "code": code,
            "closes": closes,
            "highs": highs,
            "lows": lows,
            "volumes": volumes,
        }
    except Exception as e:
        logger.warning(f"异动检测K线获取失败({code}): {e}")
        return None
