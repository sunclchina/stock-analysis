"""
M03 预警计算引擎 — 风险评分模块（按设计文档完全重写）

规则来源：6.智能预警模块.md §3.7 风险预警

计分体系：
- 基础分：50分
- 日线固定项（每日开盘前计算一次）：
  · 均线空头排列 +10，多头排列 -10
  · 下跌通道 +12，上涨通道 -12
  · MACD死叉+绿柱放大 +8，金叉+红柱放大 -8
  · 日线顶部反转 +12，底部反转 -12
- 实时动态项（每分钟/5分钟重算）：
  · 价格破MA20 +8 / 站上MA20 -8
  · 放量下跌 +10 / 放量上涨 -8
  · RSI>70拐头 +8 / RSI<30拐头 -8
  · 1分钟K线跌幅≥0.5% +10 / 涨幅≥0.5% -8
  · 空头共振 +15 / 多头共振 -15

风险等级（0-100）：
- 0-20: 🟢 极低风险
- 21-40: 🟡 低风险
- 41-60: 🟠 中风险
- 61-80: 🔴 高风险
- 81-100: ⚫ 极高风险

非交易时段：日线固定项照常计算，实时动态项用收盘数据做静态替代。
"""

from typing import Optional, Dict, Any, List
import math

from backend.services.warning_engine.price import WarningResult


# 设计文档颜色等级
RISK_LEVELS = [
    (0, 20, "green", "极低风险"),
    (21, 40, "yellow", "低风险"),
    (41, 60, "orange", "中风险"),
    (61, 80, "red", "高风险"),
    (81, 100, "black", "极高风险"),
]


def score_to_color(score: float, thresholds=None) -> str:
    for lo, hi, color, _ in RISK_LEVELS:
        if lo <= score <= hi:
            return color
    return "black"


def score_to_label(score: float) -> str:
    for lo, hi, _, label in RISK_LEVELS:
        if lo <= score <= hi:
            return label
    return "极高风险"


def score_to_level(score: float, thresholds=None) -> str:
    """风险分数转预警等级（兼容旧接口）"""
    level_map = {"green": "info", "yellow": "warning", "orange": "danger", "red": "danger", "black": "critical"}
    for lo, hi, color, _ in RISK_LEVELS:
        if lo <= score <= hi:
            return level_map.get(color, "info")
    return "critical"


# ─── 日线固定项计算 ─────────────────────────────

def calc_ma_alignment(closes: List[float], ma5: float = None, ma10: float = None, ma20: float = None) -> int:
    """均线排列：多头排列 -10，空头排列 +10"""
    if not closes or len(closes) < 20:
        return 0
    try:
        from backend.utils.indicators import calc_ma as ma_fn
        m5 = ma5 or (ma_fn(closes, 5)[-1] if len(closes) >= 5 else None)
        m10 = ma10 or (ma_fn(closes, 10)[-1] if len(closes) >= 10 else None)
        m20 = ma20 or (ma_fn(closes, 20)[-1] if len(closes) >= 20 else None)
        if m5 and m10 and m20:
            if m5 > m10 > m20:
                return -10  # 多头排列
            elif m5 < m10 < m20:
                return 10   # 空头排列
    except Exception:
        pass
    return 0


def calc_channel(closes: List[float]) -> int:
    """上涨/下跌通道 +12/-12"""
    if not closes or len(closes) < 20:
        return 0
    half = len(closes) // 2
    first_half = sum(closes[:half]) / half
    second_half = sum(closes[half:]) / half
    diff = (second_half - first_half) / first_half * 100 if first_half > 0 else 0
    if diff > 3:
        return -12  # 上涨通道
    elif diff < -3:
        return 12   # 下跌通道
    return 0


def calc_macd_score(closes: List[float]) -> int:
    """MACD死叉+绿柱放大 +8 / 金叉+红柱放大 -8"""
    if not closes or len(closes) < 35:
        return 0
    try:
        # 简单MACD计算
        def ema(data, period):
            if len(data) < period:
                return None
            k = 2 / (period + 1)
            result = [data[0]]
            for d in data[1:]:
                result.append(d * k + result[-1] * (1 - k))
            return result[-1]
        close_ema12 = ema(closes, 12)
        close_ema26 = ema(closes, 26)
        if close_ema12 is None or close_ema26 is None:
            return 0
        dif = close_ema12 - close_ema26
        # 判断最近两根DIF的走向
        if len(closes) >= 35:
            close_ema12_prev = ema(closes[:-1], 12)
            close_ema26_prev = ema(closes[:-1], 26)
            if close_ema12_prev and close_ema26_prev:
                dif_prev = close_ema12_prev - close_ema26_prev
                if dif > 0 and dif > dif_prev:
                    return -8  # 金叉+红柱放大
                elif dif < 0 and dif < dif_prev:
                    return 8   # 死叉+绿柱放大
    except Exception:
        pass
    return 0


def calc_reversal_pattern(closes: List[float]) -> int:
    """日线顶部反转 +12 / 底部反转 -12"""
    if not closes or len(closes) < 10:
        return 0
    try:
        recent = closes[-5:]
        older = closes[-10:-5]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        if older_avg > 0:
            ratio = (recent_avg - older_avg) / older_avg * 100
            # 顶部反转：前5天涨后5天跌
            if older_avg > sum(closes[-8:-5]) / 3 * 1.02 and recent_avg < older_avg * 0.98:
                return 12
            # 底部反转：前5天跌后5天涨
            if older_avg < sum(closes[-8:-5]) / 3 * 0.98 and recent_avg > older_avg * 1.02:
                return -12
    except Exception:
        pass
    return 0


# ─── 实时动态项计算 ─────────────────────────────

def calc_price_vs_ma20(price: float, closes: List[float], is_trading_hours: bool) -> int:
    """实时价跌破MA20 +8 / 站上MA20 -8"""
    if price <= 0 or not closes or len(closes) < 20:
        return 0
    try:
        from backend.utils.indicators import calc_ma as ma_fn
        ma20 = ma_fn(closes, 20)[-1] if len(closes) >= 20 else None
        if ma20 and ma20 > 0:
            if price < ma20:
                return 8   # 跌破MA20
            elif price > ma20:
                return -8  # 站上MA20
    except Exception:
        pass
    return 0


def calc_volume_price(price: float, pre_close: float, volumes: List[float], closes: List[float], is_trading_hours: bool) -> int:
    """放量下跌/上涨"""
    if not volumes or len(volumes) < 5:
        return 0
    if is_trading_hours and len(volumes) >= 30:
        # 实时：最近5分钟 vs 30分钟均值
        recent_5 = sum(volumes[-5:]) / 5
        avg_30 = sum(volumes[-30:]) / 30
        ratio = recent_5 / avg_30 if avg_30 > 0 else 1
        change_pct = (price - pre_close) / pre_close * 100 if pre_close > 0 else 0
        if ratio > 1.2 and change_pct < -0.5:
            return 10
        elif ratio > 1.2 and change_pct > 0.5:
            return -8
    else:
        # 非交易时段：用全天量价结构替代
        # 当日放量收跌/涨
        if len(volumes) >= 20 and len(closes) >= 20:
            avg_5d = sum(volumes[-20:-5]) / 15 if len(volumes) >= 20 else 0
            today_vol = volumes[-1] if volumes else 0
            today_change = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 and closes[-2] > 0 else 0
            if today_vol > avg_5d * 1.2 and today_change < -0.5:
                return 10
            elif today_vol > avg_5d * 1.2 and today_change > 0.5:
                return -8
    return 0


def calc_rsi_score(closes: List[float], price: float, is_trading_hours: bool) -> int:
    """RSI>70向下拐头 +8 / RSI<30向上拐头 -8"""
    if not closes or len(closes) < 15:
        return 0
    try:
        from backend.services.warning_engine.resonance import score_rsi
        result = score_rsi(closes, {})
        rsi_value = result.get("value", 50)
        rsi_signal = result.get("signal", "")
        if rsi_value > 70 and rsi_signal in ("bearish", "overbought"):
            return 8
        elif rsi_value < 30 and rsi_signal in ("bullish", "oversold"):
            return -8
    except Exception:
        pass
    return 0


def calc_kline_change(closes: List[float], is_trading_hours: bool) -> int:
    """1分钟K线涨幅/跌幅≥0.5%（非交易时段计0分）"""
    if not is_trading_hours:
        return 0  # 非交易时段直接作废
    if len(closes) < 2:
        return 0
    change = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
    if change <= -0.5:
        return 10
    elif change >= 0.5:
        return -8
    return 0


def calc_resonance_score(is_bearish_resonance: bool, is_bullish_resonance: bool) -> int:
    """共振评分：空头共振 +15 / 多头共振 -15"""
    if is_bearish_resonance:
        return 15
    elif is_bullish_resonance:
        return -15
    return 0


def is_bearish_resonance(daily_score: int, dynamic_score: int) -> bool:
    """判定是否空头共振：多项指标一致偏空"""
    return daily_score >= 10 and dynamic_score >= 10


def is_bullish_resonance(daily_score: int, dynamic_score: int) -> bool:
    """判定是否多头共振：多项指标一致偏多"""
    return daily_score <= -10 and dynamic_score <= -10


# ─── 主函数 ─────────────────────────────────────

def check_risk_score(
    code: str,
    name: str,
    closes: Optional[List[float]] = None,
    price: float = 0,
    pre_close: float = 0,
    volumes: Optional[List[float]] = None,
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    is_trading_hours: bool = False,
    finance_color: str = "gray",
    event_color: str = "gray",
) -> WarningResult:
    """
    按设计文档6.3.7节计算风险评分。

    Args:
        code: 股票代码
        name: 股票名称
        closes: 日线收盘价序列
        price: 当前价
        pre_close: 昨收价
        volumes: 成交量序列
        is_trading_hours: 是否交易时段

    Returns:
        风险评分结果
    """
    closes = closes or []
    volumes = volumes or []

    # ── 1. 日线固定项（非交易时段照常计算）──
    daily_score = 0
    daily_items = {}

    ma_alignment = calc_ma_alignment(closes)
    daily_score += ma_alignment
    daily_items["ma_alignment"] = ma_alignment

    channel = calc_channel(closes)
    daily_score += channel
    daily_items["channel"] = channel

    macd = calc_macd_score(closes)
    daily_score += macd
    daily_items["macd"] = macd

    reversal = calc_reversal_pattern(closes)
    daily_score += reversal
    daily_items["reversal"] = reversal

    # ── 2. 实时动态项（非交易时段做静态替代）──
    dynamic_score = 0
    dynamic_items = {}

    p_ma20 = calc_price_vs_ma20(price, closes, is_trading_hours)
    dynamic_score += p_ma20
    dynamic_items["price_vs_ma20"] = p_ma20

    vol_price = calc_volume_price(price, pre_close, volumes, closes, is_trading_hours)
    dynamic_score += vol_price
    dynamic_items["volume_price"] = vol_price

    rsi = calc_rsi_score(closes, price, is_trading_hours)
    dynamic_score += rsi
    dynamic_items["rsi"] = rsi

    kline_chg = calc_kline_change(closes, is_trading_hours)
    dynamic_score += kline_chg
    dynamic_items["kline_change"] = kline_chg

    bearish_res = is_bearish_resonance(daily_score, dynamic_score)
    bullish_res = is_bullish_resonance(daily_score, dynamic_score)
    res = calc_resonance_score(bearish_res, bullish_res)
    dynamic_score += res
    dynamic_items["resonance"] = res
    dynamic_items["bearish_resonance"] = bearish_res
    dynamic_items["bullish_resonance"] = bullish_res

    # ── 3. 总分 ──
    total = 50 + daily_score + dynamic_score
    total = max(0, min(100, total))

    # ── 4. 强制覆盖 ──
    force_black = (finance_color == "black") or (event_color == "black")
    if force_black:
        total = 100
        dynamic_items["force_override"] = "财务/突发为⚫，强制最高风险"

    # ── 5. 颜色等级 ──
    color = score_to_color(total)
    level_map = {"green": "info", "yellow": "warning", "orange": "danger", "red": "danger", "black": "critical"}
    level = level_map.get(color, "info")
    label = score_to_label(total)

    # 构建明细
    detail = {
        "risk_score": round(total, 2),
        "base_score": 50,
        "daily_score": daily_score,
        "daily_items": daily_items,
        "dynamic_score": dynamic_score,
        "dynamic_items": dynamic_items,
        "color_label": label,
    }

    title = f"{name}({code}) 风险评分 {total:.0f}/100【{label}】"

    return WarningResult(
        code=code,
        warning_type="risk",
        warning_level=level,
        title=title,
        detail=str(detail),
        indicator_color=color,
        triggered=True,
    )
