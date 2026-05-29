"""
M03 预警计算引擎 — 价格预警模块（按设计文档6.3.1节完全重写）

规则来源：6.智能预警模块.md §3.1 价格预警

颜色判定（4色+⬜）：
🟢 安全 — 低位超跌/负乖离>8%/站上MA20/布林下轨企稳
🟡 关注 — 中位震荡/乖离±5%内/布林中轨附近
🔴 风险 — 高位>70%/正乖离>12%/前高压力/布林上轨钝化
🔵 突破 — 跌破MA20或前低/突破布林上下轨/放量突破关键位

需要数据：日线K线（至少250条）+ 实时价
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import statistics
import math


@dataclass
class WarningResult:
    """预警计算结果"""
    code: str
    warning_type: str
    warning_level: str
    title: str
    detail: str
    indicator_color: str
    triggered: bool = False


def calc_ma(closes: List[float], period: int) -> Optional[float]:
    """计算移动平均"""
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calc_bollinger(closes: List[float], period: int = 20, std_mult: float = 2.0):
    """计算布林带"""
    if len(closes) < period:
        return None, None, None
    band = closes[-period:]
    mid = sum(band) / period
    variance = sum((x - mid) ** 2 for x in band) / period
    std = math.sqrt(variance)
    return mid, mid + std_mult * std, mid - std_mult * std


def check_price_warning_design(
    code: str,
    name: str,
    price: float,
    closes: List[float],
    highs_250: List[float] = None,
    lows_250: List[float] = None,
    volumes: List[float] = None,
) -> WarningResult:
    """
    按设计文档6.3.1节规则计算价格预警颜色。

    Args:
        code: 股票代码
        name: 股票名称
        price: 当前价格
        closes: 日线收盘价序列（至少250条最佳）
        highs_250: 近250日最高价序列
        lows_250: 近250日最低价序列
        volumes: 成交量序列

    Returns:
        价格预警结果
    """
    # 默认颜色
    result = WarningResult(
        code=code, warning_type="price",
        warning_level="info", title="", detail="{}",
        indicator_color="gray", triggered=False,
    )

    if price <= 0 or not closes:
        return result

    # ── 1. 计算相对价位（近250日价格区间位置）──
    if highs_250 and lows_250:
        high_250 = max(highs_250)
        low_250 = min(lows_250)
    elif len(closes) >= 20:
        high_250 = max(closes[-250:]) if len(closes) >= 250 else max(closes)
        low_250 = min(closes[-250:]) if len(closes) >= 250 else min(closes)
    else:
        high_250 = price * 1.2
        low_250 = price * 0.8

    range_width = high_250 - low_250
    relative_pos = (price - low_250) / range_width * 100 if range_width > 0 else 50

    # ── 2. 计算乖离率（相对MA20）──
    ma20 = calc_ma(closes, 20) if len(closes) >= 20 else None
    bias = (price - ma20) / ma20 * 100 if ma20 and ma20 > 0 else 0

    # ── 3. 布林带计算 ──
    boll_mid, boll_up, boll_down = calc_bollinger(closes, 20, 2.0) if len(closes) >= 20 else (None, None, None)

    # ── 4. 成交量分析（最近5分钟相对30分钟均值）──
    volume_ratio = 1.0
    if volumes and len(volumes) >= 30:
        recent_5 = sum(volumes[-5:]) / 5
        avg_30 = sum(volumes[-30:]) / 30
        volume_ratio = recent_5 / avg_30 if avg_30 > 0 else 1.0

    # ── 5. MA20支撑判断 ──
    above_ma20 = price > ma20 if ma20 else False

    # ── 6. 布林带位置判断 ──
    near_boll_up = False
    near_boll_down = False
    near_boll_mid = False
    if boll_up and boll_down and boll_mid:
        boll_range = boll_up - boll_down
        if boll_range > 0:
            boll_pos = (price - boll_down) / boll_range
            near_boll_up = boll_pos > 0.9
            near_boll_down = boll_pos < 0.1
            near_boll_mid = 0.4 <= boll_pos <= 0.6

    # ── 7. 前低支撑 / 前高压力 ──
    near_previous_low = False
    near_previous_high = False
    if len(closes) >= 10:
        recent_low = min(closes[-10:])
        recent_high = max(closes[-10:])
        near_previous_low = price <= recent_low * 1.03  # 前低上3%内
        near_previous_high = price >= recent_high * 0.97  # 前高下3%内

    # ── 颜色判定（按设计文档规则） ──
    color = "gray"
    reasons = []

    # 🟡 先检查关注条件
    is_yellow = False
    # 条件：相对价位 20%-70% 且乖离 ±5% 内
    if 20 <= relative_pos <= 70 and abs(bias) <= 5:
        is_yellow = True
    # 条件：布林带中轨附近
    if near_boll_mid:
        is_yellow = True
    # 条件：小幅偏离支撑/压力（波动<3%）
    if near_previous_low or near_previous_high:
        if abs(bias) <= 3:
            is_yellow = True

    # 🟢 安全条件
    is_green = False
    # 条件：相对价位 < 20%（低位超跌）
    if relative_pos < 20:
        is_green = True
        reasons.append(f"低位超跌(相对价位{relative_pos:.0f}%)")
    # 条件：负乖离率 > 8%（深度超跌）
    if bias < -8:
        is_green = True
        reasons.append(f"深度超跌(乖离率{bias:.1f}%)")
    # 条件：站上MA20且前低支撑有效
    if above_ma20 and near_previous_low:
        is_green = True
        reasons.append("站上MA20且前低支撑")
    # 条件：贴近布林下轨企稳
    if near_boll_down:
        is_green = True
        reasons.append("布林下轨企稳")

    # 🔴 风险条件
    is_red = False
    if relative_pos > 70:
        is_red = True
        reasons.append(f"高位(相对价位{relative_pos:.0f}%)")
    if bias > 12:
        is_red = True
        reasons.append(f"正乖离过{bias:.1f}%")
    if near_previous_high:
        is_red = True
        reasons.append("临近前高压力")
    # 布林上轨钝化
    if boll_up and price > boll_up and boll_mid:
        near_boll_top_ratio = (price - boll_up) / (boll_up - boll_mid) if (boll_up - boll_mid) > 0 else 0
        if near_boll_top_ratio > 0.3:
            is_red = True
            reasons.append("布林上轨钝化")

    # 🔵 突破条件
    is_purple = False
    # 跌破MA20或前低
    if ma20 and price < ma20 * 0.98:
        is_purple = True
        reasons.append(f"跌破MA20({ma20:.2f})")
    # 突破布林上下轨
    if boll_up and price > boll_up * 1.01:
        is_purple = True
        reasons.append("突破布林上轨")
    if boll_down and price < boll_down * 0.99:
        is_purple = True
        reasons.append("跌破布林下轨")
    # 放量突破关键位（成交量>1.5倍均值）
    if volume_ratio > 1.5 and (is_purple or is_red):
        reasons.append(f"放量{volume_ratio:.1f}倍")
        is_purple = True

    # ── 按优先级确定最终颜色（最高的优先） ──
    if is_purple:
        color = "blue"  # 🔵 设计文档中的蓝色 = 极端/突破
        level = "danger"
    elif is_red:
        color = "red"     # 🔴 风险
        level = "warning"
    elif is_green:
        color = "green"   # 🟢 安全
        level = "info"
    elif is_yellow:
        color = "yellow"  # 🟡 关注
        level = "info"
    else:
        color = "gray"
        level = "info"

    detail = {
        "price": round(price, 2),
        "relative_pos": round(relative_pos, 1),
        "bias": round(bias, 2),
        "ma20": round(ma20, 2) if ma20 else None,
        "boll_mid": round(boll_mid, 2) if boll_mid else None,
        "boll_up": round(boll_up, 2) if boll_up else None,
        "boll_down": round(boll_down, 2) if boll_down else None,
        "volume_ratio": round(volume_ratio, 2),
    }

    return WarningResult(
        code=code, warning_type="price",
        warning_level=level,
        title="; ".join(reasons) if reasons else "",
        detail=str(detail),
        indicator_color=color,
        triggered=color not in ("gray",),
    )


# ====== 以下保留旧函数，供原有预警引擎及其他模块引用 ======

DEFAULT_PRICE_WARNING_THRESHOLD = 0.05
DEFAULT_UPDOWN_WARNING_THRESHOLD = {
    "warning": 0.03, "danger": 0.07, "critical": 0.10,
}


def check_price_warning(code, name, price, pre_close, threshold=0.05):
    """旧版价格预警（保留兼容）"""
    if pre_close <= 0 or price <= 0:
        return None
    change_pct = (price - pre_close) / pre_close
    abs_pct = abs(change_pct)
    if abs_pct < threshold:
        return None
    if abs_pct >= 0.10:
        level, color = "critical", "purple"
    elif abs_pct >= 0.07:
        level, color = "danger", "red"
    elif abs_pct >= 0.05:
        level, color = "warning", "yellow"
    else:
        level, color = "info", "green"
    direc = "上涨" if change_pct > 0 else "下跌"
    return WarningResult(code=code, warning_type="price", warning_level=level,
        title=f"{name}({code}) {direc} {abs_pct*100:.1f}%", detail="",
        indicator_color=color, triggered=True)


def check_updown_warning(code, name, price, open_price, thresholds=None):
    """旧版涨跌预警（保留兼容）"""
    if thresholds is None:
        thresholds = DEFAULT_UPDOWN_WARNING_THRESHOLD
    if open_price <= 0 or price <= 0:
        return None
    change = (price - open_price) / open_price
    abs_c = abs(change)
    if abs_c < thresholds.get("warning", 0.03):
        return None
    if abs_c >= thresholds.get("critical", 0.10):
        level, color = "critical", "purple"
    elif abs_c >= thresholds.get("danger", 0.07):
        level, color = "danger", "red"
    elif abs_c >= thresholds.get("warning", 0.03):
        level, color = "warning", "yellow"
    else:
        level, color = "info", "gray"
    direc = "大涨" if change > 0 else "大跌"
    return WarningResult(code=code, warning_type="updown", warning_level=level,
        title=f"{name}({code}) 日内{direc} {abs_c*100:.1f}%", detail="",
        indicator_color=color, triggered=True)


def check_warnings_for_stock(code, name, price, open_price, pre_close, thresholds=None):
    """旧版对所有基础预警检查（保留兼容）"""
    if thresholds is None:
        thresholds = {}
    results = []
    pt = thresholds.get("price_threshold", DEFAULT_PRICE_WARNING_THRESHOLD)
    pr = check_price_warning(code, name, price, pre_close, pt)
    if pr:
        results.append(pr)
    ut = thresholds.get("updown_thresholds", DEFAULT_UPDOWN_WARNING_THRESHOLD)
    ur = check_updown_warning(code, name, price, open_price, ut)
    if ur:
        results.append(ur)
    return results


def check_updown_warning_design(
    code: str, name: str,
    price: float, open_price: float, pre_close: float,
    closes: list = None, volumes: list = None,
    is_trading_hours: bool = False,
) -> WarningResult:
    """
    按设计文档6.3.2节计算涨跌预警。

    非交易时段：用日线收盘/开盘价做静态替代，冻结颜色。
    """
    closes = closes or []
    volumes = volumes or []

    # 计算相对价位（250日区间）
    relative_pos = 50
    if len(closes) >= 20:
        h = max(closes[-250:]) if len(closes) >= 250 else max(closes)
        l = min(closes[-250:]) if len(closes) >= 250 else min(closes)
        rng = h - l
        relative_pos = (price - l) / rng * 100 if rng > 0 else 50

    # 计算乖离率（MA20）
    from backend.utils.indicators import calc_ma as calc_ma_fn
    bias = 0
    if len(closes) >= 20:
        ma20_vals = calc_ma_fn(closes, 20)
        for v in reversed(ma20_vals):
            if v and v > 0:
                bias = (price - v) / v * 100
                break

    # 涨跌幅
    change_pct = (price - pre_close) / pre_close * 100 if pre_close > 0 else 0
    change_from_open = (price - open_price) / open_price * 100 if open_price > 0 else 0

    # 全天涨跌幅
    daily_change = change_pct

    # 成交量比（近5日均量 / 近20日均量）
    vol_ratio = 1.0
    if len(volumes) >= 20:
        r5 = sum(volumes[-5:]) / 5
        a20 = sum(volumes[-20:]) / 20
        vol_ratio = r5 / a20 if a20 > 0 else 1.0

    # ── 颜色判定（优先级：🔴 > 🟢 > 🟡 > ⬜）──
    color = "gray"
    reasons = []

    # 🔴 风险条件
    is_red = False
    # 涨幅≥7%且高位
    if change_pct >= 7 and relative_pos > 70:
        is_red = True
        reasons.append(f"涨{change_pct:.1f}%且高位")
    # 跌幅≤-7%
    if change_pct <= -7:
        is_red = True
        reasons.append(f"跌{abs(change_pct):.1f}%")
    # 放量大跌（近5分钟量>当日均量×1.2且跌幅>0.5%）
    if vol_ratio > 1.2 and change_pct < -0.5:
        is_red = True
        reasons.append(f"放量大跌(量{vol_ratio:.1f}倍)")
    # 连续20分钟：非交易时段用日线替代→累计跌幅>4%
    if daily_change < -4:
        is_red = True
        reasons.append(f"日跌幅{abs(daily_change):.1f}%")
    # 上涨缩量且高位
    if vol_ratio < 0.8 and relative_pos > 70 and change_pct > 0:
        is_red = True
        reasons.append("上涨缩量")

    # 🟢 安全条件
    is_green = False
    # 涨幅3-6.9%且相对价位<60%
    if 3 <= change_pct < 7 and relative_pos < 60:
        is_green = True
        reasons.append(f"涨{change_pct:.1f}%且低位")
    # 放量大涨
    if vol_ratio > 1.2 and change_pct > 0.5:
        is_green = True
        reasons.append(f"放量大涨(量{vol_ratio:.1f}倍)")

    # 🔵 突破条件
    is_blue = False
    # 跌停
    if change_pct <= -9.9:
        is_blue = True
        reasons.append("跌停")
    # 放量大跌
    if vol_ratio > 1.2 and change_pct < -0.5:
        is_blue = True
    # 连续涨跌停
    if abs(change_pct) >= 9.9:
        is_blue = True
        reasons.append("极端涨跌")
    # 振幅>3%
    if abs(change_from_open) > 3 or abs(change_pct) > 3:
        if abs(change_pct) > 3:
            is_blue = True

    # 🟡 关注条件（剩余默认）
    is_yellow = False
    if abs(change_pct) <= 3:
        is_yellow = True
    if 3 <= change_pct < 7 and relative_pos > 70:
        is_yellow = True
        reasons.append(f"涨{change_pct:.1f}%但高位")

    # 优先级
    if is_blue:
        color = "blue"  # 🔵
        level = "danger"
    elif is_red:
        color = "red"     # 🔴
        level = "warning"
    elif is_green:
        color = "green"   # 🟢
        level = "info"
    elif is_yellow:
        color = "yellow"  # 🟡
        level = "info"
    else:
        color = "gray"
        level = "info"

    title = "; ".join(reasons) if reasons else ""
    return WarningResult(
        code=code, warning_type="updown",
        warning_level=level, title=title,
        detail=str({"change_pct": round(change_pct, 2), "vol_ratio": round(vol_ratio, 2)}),
        indicator_color=color,
        triggered=color not in ("gray", "yellow"),
    )
