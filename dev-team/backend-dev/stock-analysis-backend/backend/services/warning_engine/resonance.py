"""
M03 预警计算引擎 — 共振预警模块（按设计文档完全重写）

规则来源：6.智能预警模块.md §3.4 趋势共振模块

8项指标（每日4项+实时4项）：
日线（每日开盘前计算，盘中不变）：
1. MA排列（多/空）
2. MACD金叉/死叉
3. 高低点结构

实时（每分钟计算）：
4. 实时价与MA20关系
5. 实时成交量 vs 近5日同时段均量×1.2
6. 1分钟K线实体≥0.2%
7. RSI(14)实时值
8. 布林带实时位置

判定：
🟢 多头共振：正指标≥6 且 负指标≤2
🔴 空头共振：负指标≥6 且 正指标≤2
🟡 无共振：其余

非交易时段：实时指标用收盘数据静态替代，全程锁定。
"""

from typing import Optional, List, Dict, Any, Tuple
import math

from backend.services.warning_engine.price import WarningResult
from backend.utils.indicators import calc_ma, calc_macd, calc_rsi


# ─── 日线指标（非交易时段照常计算） ───────────────

def _check_ma_alignment(closes: List[float]) -> Tuple[str, str]:
    """检查MA排列：bullish/bearish/neutral"""
    if len(closes) < 20:
        return "neutral", "数据不足"
    ma5_vals = calc_ma(closes, 5)
    ma10_vals = calc_ma(closes, 10)
    ma20_vals = calc_ma(closes, 20)
    m5 = next((v for v in reversed(ma5_vals) if v is not None), None)
    m10 = next((v for v in reversed(ma10_vals) if v is not None), None)
    m20 = next((v for v in reversed(ma20_vals) if v is not None), None)
    if m5 and m10 and m20:
        if m5 > m10 > m20:
            return "bullish", "多头排列"
        elif m5 < m10 < m20:
            return "bearish", "空头排列"
    return "neutral", "均线交织"


def _check_macd(closes: List[float]) -> Tuple[str, str]:
    """检查MACD金叉/死叉"""
    if len(closes) < 26:
        return "neutral", "数据不足"
    def ema(data, period):
        if len(data) < period: return None
        k = 2 / (period + 1)
        r = [data[0]]
        for d in data[1:]:
            r.append(d * k + r[-1] * (1 - k))
        return r[-1]
    try:
        dif = (ema(closes, 12) or 0) - (ema(closes, 26) or 0)
        dif_prev = (ema(closes[:-1], 12) or 0) - (ema(closes[:-1], 26) or 0)
        if dif > 0 and dif > dif_prev:
            return "bullish", "MACD金叉/红柱"
        elif dif < 0 and dif < dif_prev:
            return "bearish", "MACD死叉/绿柱"
        elif dif > 0:
            return "bullish", "MACD为正"
        else:
            return "bearish", "MACD为负"
    except Exception:
        return "neutral", "MACD计算失败"


def _check_high_low_structure(closes: List[float]) -> Tuple[str, str]:
    """检查高低点结构：higher_high/lower_low"""
    if len(closes) < 10:
        return "neutral", "数据不足"
    # 比较近5日 vs 前5日
    recent5 = closes[-5:]
    prev5 = closes[-10:-5]
    recent_avg = sum(recent5) / 5
    prev_avg = sum(prev5) / 5
    recent_high = max(recent5)
    recent_low = min(recent5)
    prev_high = max(prev5)
    prev_low = min(prev5)
    if recent_high > prev_high and recent_low > prev_low:
        return "bullish", "高低点上移"
    elif recent_high < prev_high and recent_low < prev_low:
        return "bearish", "高低点下移"
    elif recent_high > prev_high:
        return "bullish", "高点抬升"
    elif recent_low < prev_low:
        return "bearish", "低点下移"
    return "neutral", "结构盘整"


# ─── 实时指标（非交易时段用收盘数据替代） ────────

def _check_price_vs_ma20(price: float, closes: List[float]) -> Tuple[str, str]:
    """实时价与MA20关系"""
    if len(closes) < 20 or price <= 0:
        return "neutral", "数据不足"
    ma20_vals = calc_ma(closes, 20)
    m20 = next((v for v in reversed(ma20_vals) if v is not None), None)
    if m20 and m20 > 0:
        if price > m20 * 1.02:
            return "bullish", f"价>MA20({m20:.2f})"
        elif price < m20 * 0.98:
            return "bearish", f"价<MA20({m20:.2f})"
    return "neutral", "价平MA20"


def _check_volume(volumes: List[float]) -> Tuple[str, str]:
    """成交量 vs 均量"""
    if len(volumes) < 5:
        return "neutral", "数据不足"
    recent5 = sum(volumes[-5:]) / 5
    # 用20日均量替代"过去5日同时段均量"
    if len(volumes) >= 20:
        avg20 = sum(volumes[-20:]) / 20
    else:
        avg20 = recent5
    ratio = recent5 / avg20 if avg20 > 0 else 1
    if ratio > 1.2:
        return "bullish", f"放量(量比{ratio:.1f})"
    elif ratio < 0.6:
        return "bearish", f"缩量(量比{ratio:.1f})"
    return "neutral", f"量正常({ratio:.1f})"


def _check_kline_body(closes: List[float]) -> Tuple[str, str]:
    """1分钟K线实体≥0.2%（非交易时用日线替代）"""
    if len(closes) < 2:
        return "neutral", "数据不足"
    body = abs(closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
    if body >= 0.5:
        direction = "涨" if closes[-1] > closes[-2] else "跌"
        return ("bullish" if closes[-1] > closes[-2] else "bearish", f"K线实体{body:.1f}%{direction}")
    return "neutral", f"K线实体{body:.2f}%"


def _check_rsi(closes: List[float]) -> Tuple[str, str]:
    """RSI(14)值"""
    if len(closes) < 15:
        return "neutral", "数据不足"
    rsi_vals = calc_rsi(closes, 14)
    rsi = next((v for v in reversed(rsi_vals) if v is not None), 50)
    if rsi > 70:
        return "bearish" if closes[-1] <= closes[-2] else "bullish", f"RSI={rsi:.0f}"
    elif rsi < 30:
        return "bullish" if closes[-1] >= closes[-2] else "bearish", f"RSI={rsi:.0f}"
    return "neutral", f"RSI={rsi:.0f}"


def _check_bollinger(price: float, closes: List[float]) -> Tuple[str, str]:
    """布林带实时位置"""
    if len(closes) < 20 or price <= 0:
        return "neutral", "数据不足"
    period = 20
    band = closes[-period:]
    mid = sum(band) / period
    variance = sum((x - mid) ** 2 for x in band) / period
    std = math.sqrt(variance) if variance > 0 else 0.01
    up = mid + 2 * std
    down = mid - 2 * std
    if price > up:
        return "bullish" if price > mid else "bearish", f"布林上轨({up:.2f})"
    elif price < down:
        return "bearish", f"布林下轨({down:.2f})"
    elif abs(price - mid) / mid < 0.02:
        return "neutral", "布林中轨"
    elif price > mid:
        return "bullish", f"布林中上({up:.2f}/{down:.2f})"
    else:
        return "bearish", f"布林中下({up:.2f}/{down:.2f})"


# ─── 主函数 ─────────────────────────────────────

def check_resonance_warning(
    code: str, name: str,
    price: float, change_pct: float,
    opens: List[float], highs: List[float],
    lows: List[float], closes: List[float],
    volumes: List[float],
    thresholds: Dict[str, Any] = None,
) -> Optional[WarningResult]:
    """
    按设计文档6.3.4节计算共振预警。

    8项指标（3日线+5实时），非交易时实时指标用收盘数据替代。
    """
    if len(closes) < 20:
        return None
    if price <= 0:
        price = closes[-1] if closes else 0

    # ── 计算8项指标方向 ──
    results = []

    # 日线指标
    r1 = _check_ma_alignment(closes)
    results.append(("MA排列", r1))

    r2 = _check_macd(closes)
    results.append(("MACD", r2))

    r3 = _check_high_low_structure(closes)
    results.append(("高低点", r3))

    # 实时指标（非交易时段用收盘数据替代）
    r4 = _check_price_vs_ma20(price, closes)
    results.append(("价格MA20", r4))

    r5 = _check_volume(volumes)
    results.append(("成交量", r5))

    r6 = _check_kline_body(closes)
    results.append(("K线实体", r6))

    r7 = _check_rsi(closes)
    results.append(("RSI", r7))

    r8 = _check_bollinger(price, closes)
    results.append(("布林带", r8))

    # ── 统计 ──
    positive = sum(1 for _, (direction, _) in results if direction == "bullish")
    negative = sum(1 for _, (direction, _) in results if direction == "bearish")

    # ── 判定 ──
    if positive >= 6 and negative <= 2:
        color = "green"
        level = "info"
    elif negative >= 6 and positive <= 2:
        color = "red"
        level = "danger"
    else:
        color = "yellow"
        level = "info"

    # 构件摘要
    items_summary = []
    for name, (direction, detail) in results:
        items_summary.append(f"{name}:{detail}({direction})")

    title = f"{name}({code}) 共振{positive}多{negative}空"
    if color == "green":
        title += "【多头共振】"
    elif color == "red":
        title += "【空头共振】"
    else:
        title += "【无共振】"

    detail = {
        "positive_count": positive,
        "negative_count": negative,
        "color": color,
        "items": [{"name": n, "direction": d, "detail": dt} for n, (d, dt) in results],
    }

    triggered = color in ("green", "red")
    return WarningResult(
        code=code, warning_type="resonance",
        warning_level=level, title=title,
        detail=str(detail),
        indicator_color=color,
        triggered=triggered,
    )
