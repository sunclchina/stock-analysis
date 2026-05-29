"""
M03 预警计算引擎 — 趋势预警模块（按设计文档完全重写）

规则来源：6.智能预警模块.md §3.3 趋势预警（混合模式）

方向判定：
🟢 上涨：价>MA5/10/20 + 多头排列 + 重心上移 + 无反转
🔴 下跌：价<MA5/10/20 + 空头排列 + 重心下移 + 无反转
🟡 震荡：不属于涨跌且无反转
🔵 反转：底部/顶部反转形态 + MACD背离/金叉死叉

非交易时段：日线收盘数据静态替代，方向+强度冻结。
"""

from typing import Optional, List, Dict, Any, Tuple
import math

from backend.services.warning_engine.price import WarningResult
from backend.utils.indicators import calc_ma

# ─── 工具函数 ─────────────────────────────────────

def _get_latest_ma(closes: List[float], period: int) -> Optional[float]:
    """获取最新均线值"""
    if len(closes) < period:
        return None
    vals = calc_ma(closes, period)
    for v in reversed(vals):
        if v is not None:
            return v
    return None


def _macd_signal(closes: List[float]) -> Tuple[Optional[str], Optional[str]]:
    """简单MACD判断：返回 (divergence_type, cross_signal)"""
    if len(closes) < 30:
        return None, None
    def ema(data, period):
        if len(data) < period: return None
        k = 2 / (period + 1)
        r = [data[0]]
        for d in data[1:]:
            r.append(d * k + r[-1] * (1 - k))
        return r[-1]
    try:
        dif = ema(closes, 12) - ema(closes, 26)
        dif_prev = ema(closes[:-1], 12) - ema(closes[:-1], 26)
        dea = ema([dif], 9) if dif else None
        # 金叉/死叉
        cross = None
        if dif_prev and dif and dea:
            if dif_prev <= dea and dif > (dea if dea else dif):
                cross = "golden_cross"
            elif dif_prev >= dea and dif < (dea if dea else dif):
                cross = "death_cross"
        # 顶底背离
        divergence = None
        if len(closes) >= 30 and dif and dif_prev:
            if closes[-1] > closes[-5] and dif < dif_prev:
                divergence = "top"  # 顶背离
            elif closes[-1] < closes[-5] and dif > dif_prev:
                divergence = "bottom"  # 底背离
        return divergence, cross
    except Exception:
        return None, None


# ─── 方向判定 ─────────────────────────────────────

def check_trend_warning(
    code: str,
    name: str,
    price: float,
    closes: List[float],
    volumes: List[float] = None,
    highs: List[float] = None,
    lows: List[float] = None,
    is_trading_hours: bool = False,
    thresholds: Dict[str, Any] = None,
) -> Optional[WarningResult]:
    """
    按设计文档6.3.3节计算趋势预警。

    Args:
        price: 当前价（非交易时段=收盘价）
        closes: 日线收盘价序列
        volumes: 成交量序列
        is_trading_hours: 是否交易时段

    Returns:
        趋势预警结果
    """
    if not closes or len(closes) < 25:
        return None
    if price <= 0:
        return None

    volumes = volumes or []
    highs = highs or []
    lows = lows or []

    # ── 计算均线 ──
    ma5 = _get_latest_ma(closes, 5)
    ma10 = _get_latest_ma(closes, 10)
    ma20 = _get_latest_ma(closes, 20)

    if ma5 is None or ma10 is None or ma20 is None:
        return None

    # ── 阶段1: 方向判定 ──
    above_ma5 = price > ma5
    above_ma10 = price > ma10
    above_ma20 = price > ma20
    below_ma5 = price < ma5
    below_ma10 = price < ma10
    below_ma20 = price < ma20

    # 多头排列：MA5 >= MA10 >= MA20
    bullish_aligned = ma5 >= ma10 >= ma20
    bearish_aligned = ma5 <= ma10 <= ma20

    # 重心方向（用最近3个日线收盘）
    upward_重心 = False
    downward_重心 = False
    if len(closes) >= 3:
        upward_重心 = closes[-1] > closes[-2] > closes[-3]
        downward_重心 = closes[-1] < closes[-2] < closes[-3]

    # MACD信号
    divergence, cross = _macd_signal(closes)

    # 成交量放大（近5日均量 vs 近20日均量）
    vol_surge = False
    if len(volumes) >= 20:
        recent5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
        avg20 = sum(volumes[-20:]) / 20
        vol_surge = recent5 > avg20 * 1.3 if avg20 > 0 else False

    # ── 判定上涨 ──
    is_up = (above_ma5 and above_ma10 and above_ma20 and
             bullish_aligned and upward_重心)

    # ── 判定下跌 ──
    is_down = (below_ma5 and below_ma10 and below_ma20 and
               bearish_aligned and downward_重心)

    # ── 判定反转 ──
    is_reversal = False
    reversal_type = None

    # 底部反转：连续3根K线收于MA20之上+成交量放大
    if not is_up and not is_down:
        if len(closes) >= 3 and ma20:
            three_above = all(c > ma20 for c in closes[-3:])
            if three_above and vol_surge:
                is_reversal = True
                reversal_type = "bottom_reversal"

    # MACD底背离+金叉
    if divergence == "bottom" and cross == "golden_cross":
        is_reversal = True
        reversal_type = "bottom_macd"

    # 顶部背离+死叉
    if divergence == "top" and cross == "death_cross":
        is_reversal = True
        reversal_type = "top_macd"

    # K线形态：底部反转形态
    if not is_reversal and len(closes) >= 10:
        # 金针探底：长下影线
        if lows and len(lows) >= 3:
            recent_low = min(lows[-3:])
            recent_high = max(highs[-3:]) if highs else price * 1.05
            body_top = price  # 收盘价近似
            shadow_bottom = recent_low
            shadow_ratio = (body_top - shadow_bottom) / (recent_high - shadow_bottom) if (recent_high - shadow_bottom) > 0 else 0
            if shadow_ratio < 0.3:  # 下影线长度占全幅<30%
                is_reversal = True
                reversal_type = "hammer"
        # 顶部反转：乌云盖顶
        if not is_reversal and len(closes) >= 5:
            if closes[-1] < closes[-2] * 0.97 and closes[-2] > closes[-3]:
                is_reversal = True
                reversal_type = "dark_cloud"

    # ── 综合判定方向 ──
    if is_reversal:
        if reversal_type in ("bottom_reversal", "bottom_macd", "hammer"):
            direction = "bullish_reversal"
        else:
            direction = "bearish_reversal"
    elif is_up:
        direction = "bullish"
    elif is_down:
        direction = "bearish"
    else:
        direction = "consolidation"

    # ── 映射颜色 ──
    if direction in ("bearish_reversal",):
        color = "blue"  # 🔵 反转（设计文档蓝色）
        level = "danger"
    elif direction in ("bullish_reversal",):
        color = "blue"  # 🔵 反转
        level = "warning"
    elif direction == "bullish":
        color = "green"   # 🟢 上涨
        level = "info"
    elif direction == "bearish":
        color = "red"     # 🔴 下跌
        level = "danger"
    else:
        color = "yellow"  # 🟡 震荡
        level = "info"

    # ── 阶段2: 趋势强度评分（仅涨/跌趋势） ──
    strength_score = 50
    if direction in ("bullish", "bearish"):
        # 均线因素
        ma_score = 0
        if ma5 and ma10 and ma20:
            spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
            if direction == "bullish":
                ma_score = min(30, max(0, spread * 10))
            else:
                ma_score = max(-30, min(0, spread * 10))

        # 价格形态因素
        price_score = 0
        if len(closes) >= 5:
            recent_trend = (closes[-1] - closes[-5]) / closes[-5] * 100 if closes[-5] > 0 else 0
            if direction == "bullish":
                price_score = min(25, max(0, recent_trend * 5))
            else:
                price_score = max(-25, min(0, recent_trend * 5))

        # 成交量因素
        vol_score = 0
        if len(volumes) >= 20:
            recent5 = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            avg20 = sum(volumes[-20:]) / 20
            if avg20 > 0:
                vol_ratio = recent5 / avg20
                if direction == "bullish":
                    vol_score = min(20, max(0, (vol_ratio - 1) * 20))
                else:
                    vol_score = max(-20, min(0, (1 - vol_ratio) * 20))

        # MACD因素
        macd_score = 0
        if cross == "golden_cross":
            macd_score = 25 if direction == "bullish" else -10
        elif cross == "death_cross":
            macd_score = -25 if direction == "bearish" else 10

        strength_score = 50 + ma_score + price_score + vol_score + macd_score
        strength_score = max(0, min(100, strength_score))

        # 下跌趋势强制 ≤ 39
        if direction == "bearish":
            strength_score = min(strength_score, 39)

    # ── 组装结果 ──
    direction_names = {
        "bullish": "上涨趋势",
        "bearish": "下跌趋势",
        "consolidation": "震荡趋势",
        "bullish_reversal": "底部反转",
        "bearish_reversal": "顶部反转",
    }
    dir_name = direction_names.get(direction, "未知")

    # 构建强度标签
    if direction in ("bullish", "bearish"):
        if strength_score >= 80:
            strength_label = "极强"
        elif strength_score >= 60:
            strength_label = "强势"
        elif strength_score >= 40:
            strength_label = "震荡偏强"
        else:
            strength_label = "震荡偏弱"
    else:
        strength_label = ""
        strength_score = 50

    title = f"{name}({code}) {dir_name}"
    if strength_label:
        title += f"({strength_label} {strength_score}分)"

    detail = {
        "direction": direction,
        "price": price,
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "strength_score": strength_score,
        "strength_label": strength_label,
        "reversal_type": reversal_type,
        "macd_divergence": divergence,
        "macd_cross": cross,
    }

    return WarningResult(
        code=code, warning_type="trend",
        warning_level=level, title=title,
        detail=str(detail),
        indicator_color=color,
        triggered=color not in ("yellow", "gray"),
    )


# ====== 以下保留旧函数，供__init__导出兼容 ======


def classify_trend_direction(ma5: float, ma10: float, ma20: float) -> str:
    """判断趋势方向（保留兼容）"""
    if ma5 > ma10 > ma20:
        return "bullish"
    elif ma5 < ma10 < ma20:
        return "bearish"
    else:
        return "consolidation"


def check_ma_breakout(price, ma5, ma10, ma20, threshold=0.03):
    """检测价格突破均线（保留兼容）"""
    if ma5 is None or ma10 is None or ma20 is None:
        return None
    above = price > ma5 * (1 + threshold) and price > ma10 * (1 + threshold) and price > ma20 * (1 + threshold)
    below = price < ma5 * (1 - threshold) and price < ma10 * (1 - threshold) and price < ma20 * (1 - threshold)
    if above:
        return "above_all"
    elif below:
        return "below_all"
    return "normal"


def check_trend_reversal(closes, ma5_vals, ma10_vals, ma20_vals):
    """检测趋势反转信号（保留兼容）"""
    if not ma5_vals or not ma10_vals:
        return None
    recent5 = [v for v in ma5_vals[-5:] if v is not None]
    recent10 = [v for v in ma10_vals[-5:] if v is not None]
    if len(recent5) < 2 or len(recent10) < 2:
        return None
    if recent5[-2] <= recent10[-2] and recent5[-1] > recent10[-1]:
        return "golden_cross"
    if recent5[-2] >= recent10[-2] and recent5[-1] < recent10[-1]:
        return "death_cross"
    return None
