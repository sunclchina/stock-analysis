"""
M04 选股引擎 — 固定规则选股（v3.0）。

五层漏斗重写（设计文档 §5.2）：
第1层：快速底层过滤（强制剔除ST/停牌/流动性差/低价/次新）
财务+事件过滤（前置，L1之后立即执行）—— 各方案差异
第2层：轻量技术指标（全部6项满足）
第3层：深度技术面精筛（强制+附加≥2+剔除）
第4层：综合评分 + 输出分级 + 容量控制

策略模板ID（与前端一致）：
1. steady_trend    — 稳健趋势型
2. reversal_breakout   — 反转突破型
3. short_term_strong — 短线强势型
"""

import json
import logging
import time
from functools import partial
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field

from backend.services.selection_engine.scorer import sort_by_score
from backend.services.selection_engine.batch_processor import BatchProcessor, batch_filter
from backend.services.selection_engine.financial_cache import financial_data_loader

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════
# 第1层：快速底层过滤（强制剔除）
# 设计文档 §5.2.1
# ═══════════════════════════════════════════════════

def filter_not_st(stock: Dict[str, Any]) -> bool:
    """非ST/ST*/退市整理期"""
    is_st = stock.get("is_st")
    if is_st is None:
        return False
    return not is_st


def filter_not_suspended(stock: Dict[str, Any]) -> bool:
    """非停牌"""
    suspended = stock.get("is_suspended")
    if suspended is None:
        return False
    return not suspended


def filter_liquidity(stock: Dict[str, Any]) -> bool:
    """流动性：日均成交额/流通市值 > 0.5%（文档§5.2.1）"""
    amount = stock.get("amount")
    if amount is None:
        return False
    amount = float(amount)
    if amount <= 0:
        return False
    circ_mv = stock.get("circ_market_value")
    if circ_mv is not None and circ_mv > 0:
        ratio = amount / float(circ_mv)
        if ratio <= 0.005:
            return False
        return True
    return amount >= 100  # 成交额 >= 100万（万元）


def filter_min_price(stock: Dict[str, Any], min_p: float = 1.0) -> bool:
    """股价 >= 最低价门槛"""
    price = stock.get("price")
    if price is None:
        return False
    return float(price) >= min_p


def filter_not_new_share(stock: Dict[str, Any]) -> bool:
    """上市时间 >= 60个交易日"""
    trade_days = stock.get("trade_days_since_listing")
    if trade_days is None:
        return True
    return trade_days >= 60


# ═══════════════════════════════════════════════════
# 财务+事件过滤（前置）
# 设计文档 §5.2.1：各方案差异
# ═══════════════════════════════════════════════════

def fin_grade_green(stock: Dict[str, Any]) -> bool:
    """财务等级🟢"""
    grade = stock.get("finance_grade") or stock.get("finance_color", "")
    if isinstance(grade, str):
        return grade.lower() in ("green", "a", "safe", "yellow")
    return False


def fin_grade_green_or_yellow(stock: Dict[str, Any]) -> bool:
    """财务等级🟢/🟡"""
    grade = stock.get("finance_grade") or stock.get("finance_color", "")
    if isinstance(grade, str):
        return grade.lower() in ("green", "a", "safe", "yellow", "b")
    return False


def fin_grade_not_red_black(stock: Dict[str, Any]) -> bool:
    """财务等级非🔴/⚫"""
    grade = stock.get("finance_grade") or stock.get("finance_color", "")
    if isinstance(grade, str):
        return grade.lower() not in ("red", "black", "d", "f")
    return True


def fin_abnormal_zero(stock: Dict[str, Any]) -> bool:
    """异常=0"""
    abnormal = stock.get("finance_abnormal_count") or stock.get("finance_abnormal", 0)
    try:
        return int(abnormal) == 0
    except (ValueError, TypeError):
        return False


def fin_abnormal_le_1(stock: Dict[str, Any]) -> bool:
    """异常≤1"""
    abnormal = stock.get("finance_abnormal_count") or stock.get("finance_abnormal", 0)
    try:
        return int(abnormal) <= 1
    except (ValueError, TypeError):
        return False


def fin_deduct_profit_positive(stock: Dict[str, Any]) -> bool:
    """扣非净利为正"""
    deduct = stock.get("deducted_profit") or stock.get("np_deducted")
    if deduct is not None:
        try:
            return float(deduct) > 0
        except (ValueError, TypeError):
            pass
    return True  # 无数据不拦截


def fin_deduct_profit_not_negative(stock: Dict[str, Any]) -> bool:
    """扣非净利不为负"""
    deduct = stock.get("deducted_profit") or stock.get("np_deducted")
    if deduct is not None:
        try:
            return float(deduct) >= 0
        except (ValueError, TypeError):
            pass
    return True


def fin_cashflow_positive(stock: Dict[str, Any]) -> bool:
    """现金流为正"""
    cf = stock.get("operate_cashflow") or stock.get("cashflow")
    if cf is not None:
        try:
            return float(cf) > 0
        except (ValueError, TypeError):
            pass
    return True


def fin_debt_ratio_le_60(stock: Dict[str, Any]) -> bool:
    """负债率≤60%"""
    dr = stock.get("debt_ratio")
    if dr is not None:
        try:
            return float(dr) <= 60.0
        except (ValueError, TypeError):
            pass
    return True


def fin_debt_ratio_le_75(stock: Dict[str, Any]) -> bool:
    """负债率≤75%"""
    dr = stock.get("debt_ratio")
    if dr is not None:
        try:
            return float(dr) <= 75.0
        except (ValueError, TypeError):
            pass
    return True


# ── 事件风险（所有方案相同）──

def event_shareholder_sell_le_5(stock: Dict[str, Any]) -> bool:
    """大股东减持≤5%"""
    reduction = stock.get("planned_reduction_pct")
    if reduction is not None:
        try:
            return float(reduction) <= 5.0
        except (ValueError, TypeError):
            pass
    return True


def event_pledge_le_90(stock: Dict[str, Any]) -> bool:
    """质押≤90%"""
    pledge = stock.get("pledge_ratio")
    if pledge is not None:
        try:
            return float(pledge) <= 90.0
        except (ValueError, TypeError):
            pass
    return True


def event_no_debt_default(stock: Dict[str, Any]) -> bool:
    """无债务违约"""
    flag = stock.get("debt_default_flag")
    if flag is not None:
        return not flag
    return True


def event_no_investigation(stock: Dict[str, Any]) -> bool:
    """无立案调查"""
    flag = stock.get("csrc_investigation_flag")
    if flag is not None:
        return not flag
    return True


def event_lawsuit_le_30pct(stock: Dict[str, Any]) -> bool:
    """无重大诉讼>净资产30%"""
    lawsuit = stock.get("lawsuit_amount")
    net_asset = stock.get("net_asset")
    if lawsuit is not None and net_asset is not None and net_asset > 0:
        try:
            return float(lawsuit) <= float(net_asset) * 0.3
        except (ValueError, TypeError):
            pass
    return True


def event_audit_standard(stock: Dict[str, Any]) -> bool:
    """审计非标排除"""
    audit = stock.get("audit_opinion")
    if audit is not None:
        return audit not in ("negative", "disclaimer", "qualified")
    return True


def event_no_fraud(stock: Dict[str, Any]) -> bool:
    """无财务造假"""
    flag = stock.get("fraud_flag")
    if flag is not None:
        return not flag
    return True


# ═══════════════════════════════════════════════════
# 第2层：轻量技术指标（全部6项满足）
# 设计文档 §5.2.2
# ═══════════════════════════════════════════════════

def l2_price_above_ma20_uptrend(stock: Dict[str, Any]) -> bool:
    """条件1：现价>MA20 且 MA20趋势向上"""
    price = stock.get("price")
    ma20 = stock.get("ma20")
    ma20_up = stock.get("ma20_trend_up")
    if any(v is None for v in (price, ma20, ma20_up)):
        return False
    return float(price) > float(ma20) and bool(ma20_up)


def l2_ma_triple_bullish(stock: Dict[str, Any]) -> bool:
    """条件2：MA5>MA10>MA20"""
    ma5 = stock.get("ma5")
    ma10 = stock.get("ma10")
    ma20 = stock.get("ma20")
    if any(v is None for v in (ma5, ma10, ma20)):
        return False
    try:
        return float(ma5) > float(ma10) > float(ma20)
    except (ValueError, TypeError):
        return False


def l2_recent_3d_up_ge_2(stock: Dict[str, Any]) -> bool:
    """条件3：近3日累计涨幅 ≥ 2%"""
    c3 = stock.get("change_pct_3d")
    if c3 is None:
        return False
    try:
        return float(c3) >= 2.0
    except (ValueError, TypeError):
        return False


def l2_price_position_30_70(stock: Dict[str, Any]) -> bool:
    """条件4：60日相对价位 30%~70%"""
    pos = stock.get("price_position")
    if pos is None:
        return False
    try:
        return 0.30 <= float(pos) <= 0.70
    except (ValueError, TypeError):
        return False


def l2_not_sharp_down_ge_neg2(stock: Dict[str, Any]) -> bool:
    """条件5：今日涨幅 ≥ -2%"""
    change = stock.get("change_pct")
    if change is None:
        return False
    try:
        return float(change) >= -2.0
    except (ValueError, TypeError):
        return False


def l2_volume_ge_5d_avg(stock: Dict[str, Any]) -> bool:
    """条件6：成交量 ≥ 近5日均量"""
    vol = stock.get("volume")
    v5 = stock.get("volume_5d_avg")
    if vol is None or v5 is None:
        return False
    try:
        return float(vol) >= float(v5)
    except (ValueError, TypeError):
        return False


L2_ALL_FILTERS = [
    l2_price_above_ma20_uptrend,
    l2_ma_triple_bullish,
    l2_recent_3d_up_ge_2,
    l2_price_position_30_70,
    l2_not_sharp_down_ge_neg2,
    l2_volume_ge_5d_avg,
]

# ── 财务+事件过滤函数分组 ──

def _build_financial_filters(strategy: str) -> List[Callable]:
    """根据策略构建财务过滤函数列表"""
    filters = []

    if strategy == "steady_trend":
        # 稳健趋势型：财务等级🟢, 异常=0, 扣非净利为正, 现金流为正, 负债率≤60%
        filters.extend([
            fin_grade_green,
            fin_abnormal_zero,
            fin_deduct_profit_positive,
            fin_cashflow_positive,
            fin_debt_ratio_le_60,
        ])
    elif strategy == "reversal_breakout":
        # 反转突破型：财务等级🟢/🟡, 异常=0, 扣非净利不为负, 现金流为正, 负债率≤75%
        filters.extend([
            fin_grade_green_or_yellow,
            fin_abnormal_zero,
            fin_deduct_profit_not_negative,
            fin_cashflow_positive,
            fin_debt_ratio_le_75,
        ])
    elif strategy == "short_term_strong":
        # 短线强势型：财务等级非🔴/⚫, 异常≤1, 不要求净利/现金流/负债率
        filters.extend([
            fin_grade_not_red_black,
            fin_abnormal_le_1,
        ])

    return filters


def _build_event_filters() -> List[Callable]:
    """构建事件风险过滤函数列表（所有方案相同）"""
    return [
        event_shareholder_sell_le_5,
        event_pledge_le_90,
        event_no_debt_default,
        event_no_investigation,
        event_lawsuit_le_30pct,
        event_audit_standard,
        event_no_fraud,
    ]


# ═══════════════════════════════════════════════════
# 第3层：深度技术面精筛
# 设计文档 §5.2.3
# ═══════════════════════════════════════════════════

# ── 强制条件（三项缺一不可）──

def l3_trend_up_or_reversal(stock: Dict[str, Any]) -> bool:
    """趋势方向🟢上涨或🔵反转"""
    direction = stock.get("trend_direction")
    if direction in ("bullish", "up", "reversal", "blue", "bullish_reversal"):
        return True
    # 公式化反转判定
    if stock.get("_is_reversal_by_formula", False):
        return True
    return False


def l3_resonance_ge_4(stock: Dict[str, Any]) -> bool:
    """多头共振≥4项"""
    pos = stock.get("resonance_positive_count") or stock.get("resonance_positive", 0)
    try:
        return int(pos) >= 4
    except (ValueError, TypeError):
        return False


def l3_risk_le_40(stock: Dict[str, Any]) -> bool:
    """风险评分≤40"""
    risk = stock.get("risk_score")
    if risk is None:
        return False
    try:
        return float(risk) <= 40
    except (ValueError, TypeError):
        return False


# ── 反转判定辅助函数 ──

def _check_reversal_by_formula(stock: Dict[str, Any]) -> bool:
    """反转定义：价格<60日高点20%以上，且10日内涨幅>8%"""
    price = stock.get("price", 0)
    high_60d = stock.get("high_60d", 0)
    change_10d = stock.get("change_pct_10d", 0)
    if high_60d and price and change_10d is not None:
        try:
            if float(price) < float(high_60d) * 0.8 and float(change_10d) > 8:
                return True
        except (ValueError, TypeError):
            pass
    return False


# ── 附加项 ──

def l3_opt_trend_strength_ge_80(stock: Dict[str, Any]) -> bool:
    """附加A：趋势强度≥80"""
    score = stock.get("trend_score")
    if score is None:
        return False
    try:
        return abs(float(score)) >= 80
    except (ValueError, TypeError):
        return False


def l3_opt_price_position_20_55(stock: Dict[str, Any]) -> bool:
    """附加B：价格20%-55%"""
    pos = stock.get("price_position")
    if pos is None:
        return False
    try:
        return 0.20 <= float(pos) <= 0.55
    except (ValueError, TypeError):
        return False


def l3_opt_price_volume_healthy(stock: Dict[str, Any]) -> bool:
    """附加C：量价健康"""
    vol_ratio = stock.get("volume_ratio")
    change = stock.get("change_pct")
    if vol_ratio is None or change is None:
        return False
    try:
        vr = float(vol_ratio)
        ch = float(change)
        if ch > 0 and vr > 1.2:
            return True
        if ch < 0 and vr < 0.8:
            return True
        return False
    except (ValueError, TypeError):
        return False


def l3_opt_macd_red_expanding(stock: Dict[str, Any]) -> bool:
    """附加D：MACD红柱放大"""
    macd_bar = stock.get("macd_bar")
    if macd_bar is None:
        macd_signal = stock.get("macd_signal")
        if macd_signal is not None:
            return macd_signal in ("golden", "bullish")
        return False
    try:
        mb = float(macd_bar)
        if mb <= 0:
            return False
        mb_prev = stock.get("macd_bar_prev")
        if mb_prev is not None:
            return mb > float(mb_prev)
        return True
    except (ValueError, TypeError):
        return False


L3_OPTIONAL_FILTERS = [
    l3_opt_trend_strength_ge_80,
    l3_opt_price_position_20_55,
    l3_opt_price_volume_healthy,
    l3_opt_macd_red_expanding,
]


# ── 剔除条件（任意1项直接剔除）──

def l3_excl_bearish_ge_3(stock: Dict[str, Any]) -> bool:
    """剔除：空头共振≥3"""
    neg = stock.get("resonance_negative_count") or stock.get("resonance_negative", 0)
    try:
        return int(neg) >= 3
    except (ValueError, TypeError):
        return False


def l3_excl_risk_ge_61(stock: Dict[str, Any]) -> bool:
    """剔除：风险≥61"""
    risk = stock.get("risk_score")
    if risk is None:
        return False
    try:
        return float(risk) >= 61
    except (ValueError, TypeError):
        return False


def l3_excl_consecutive_drop_volume(stock: Dict[str, Any]) -> bool:
    """剔除：连续放量下跌"""
    consec = stock.get("consecutive_drop_volume_days")
    if consec is not None:
        try:
            return int(consec) >= 3
        except (ValueError, TypeError):
            pass

    closes = stock.get("closes", [])
    volumes = stock.get("volumes", [])
    if len(closes) < 6 or len(volumes) < 6:
        return False
    v5 = stock.get("volume_5d_avg", 0)
    if v5 <= 0:
        avg_5 = sum(volumes[-6:-1]) / 5
        v5 = avg_5
    if v5 <= 0:
        return False
    try:
        count = 0
        for i in range(3):
            idx = -(i + 1)
            prev_idx = idx - 1
            if closes[prev_idx] <= 0:
                continue
            daily_change = (closes[idx] - closes[prev_idx]) / closes[prev_idx] * 100
            daily_ratio = volumes[idx] / v5
            if daily_change < -2.0 and daily_ratio >= 1.2:
                count += 1
            else:
                break
        return count >= 3
    except (IndexError, ValueError, TypeError):
        return False


def l3_excl_deviation_gt_12(stock: Dict[str, Any]) -> bool:
    """剔除：乖离率>+12%"""
    dev = stock.get("deviation_rate")
    if dev is None:
        return False
    try:
        return float(dev) > 12.0
    except (ValueError, TypeError):
        return False


def l3_excl_breakdown(stock: Dict[str, Any]) -> bool:
    """剔除：破位下跌"""
    breakdown = stock.get("breakdown_signal")
    if breakdown is None:
        return False
    return bool(breakdown)


L3_EXCLUSION_FILTERS = [
    l3_excl_bearish_ge_3,
    l3_excl_risk_ge_61,
    l3_excl_consecutive_drop_volume,
    l3_excl_deviation_gt_12,
    l3_excl_breakdown,
]


# ── 方案替换规则辅助 ──

def l3_volume_ratio_ge_1_5(stock: Dict[str, Any]) -> bool:
    """量比/放量≥1.5倍（用于替换规则）"""
    vr = stock.get("volume_ratio")
    if vr is None:
        return False
    try:
        return float(vr) >= 1.5
    except (ValueError, TypeError):
        return False


# ═══════════════════════════════════════════════════
# L3 数据富集（内联技术指标计算）
# ═══════════════════════════════════════════════════

def _enrich_technicals(stock: Dict[str, Any]) -> Dict[str, Any]:
    """对单只股票计算趋势/共振/风险指标"""
    price = stock.get("price", 0)
    ma5 = stock.get("ma5", 0)
    ma10 = stock.get("ma10", 0)
    ma20 = stock.get("ma20", 0)
    change_pct = stock.get("change_pct", 0)
    change_pct_3d = stock.get("change_pct_3d", 0)
    volume_ratio = stock.get("volume_ratio", 1.0)
    price_position = stock.get("price_position", 0.5)
    deviation_rate = stock.get("deviation_rate", 0)

    if price <= 0 or ma20 <= 0:
        return stock

    try:
        price = float(price)
        ma5 = float(ma5)
        ma10 = float(ma10)
        ma20 = float(ma20)
        change_pct = float(change_pct)
        change_pct_3d = float(change_pct_3d)
        volume_ratio = float(volume_ratio)
        price_position = float(price_position)
        deviation_rate = float(deviation_rate)
    except (ValueError, TypeError):
        return stock

    above_ma5 = price > ma5
    above_ma10 = price > ma10
    above_ma20 = price > ma20
    bullish_aligned = ma5 > ma10 > ma20
    bearish_aligned = ma5 < ma10 < ma20

    # 趋势方向
    if above_ma5 and above_ma10 and above_ma20 and bullish_aligned:
        trend_direction = "bullish"
        strength = min(100, 50 + int(abs(deviation_rate) * 3) +
                       (10 if change_pct_3d >= 2 else 0) +
                       (10 if volume_ratio >= 1.0 else 0))
    elif bearish_aligned:
        trend_direction = "bearish"
        strength = max(0, 50 - int(abs(deviation_rate) * 2))
    elif above_ma20 and not bearish_aligned:
        if change_pct_3d >= 0 and change_pct >= -1:
            trend_direction = "bullish_reversal"
            strength = 50 + (10 if volume_ratio >= 1.0 else 0)
        else:
            trend_direction = "consolidation"
            strength = 50
    else:
        trend_direction = "consolidation"
        strength = 50

    stock["trend_direction"] = trend_direction
    stock["trend_score"] = min(100, max(0, strength))

    # 共振评分（8项信号）
    pos = 0
    neg = 0

    if bullish_aligned:
        pos += 1
    elif bearish_aligned:
        neg += 1

    if above_ma20:
        pos += 1
    else:
        neg += 1

    if change_pct >= 0 and volume_ratio >= 0.8:
        pos += 1
    elif change_pct < -2 and volume_ratio > 1.2:
        neg += 1

    if change_pct_3d > 0:
        pos += 1
    elif change_pct_3d < -3:
        neg += 1

    if 0.25 < price_position < 0.70:
        pos += 1
    elif price_position > 0.90:
        neg += 1

    if ma5 > ma10:
        pos += 1
    else:
        neg += 1

    if volume_ratio > 0.6:
        pos += 1
    elif volume_ratio < 0.3:
        neg += 1

    if abs(deviation_rate) < 8:
        pos += 1
    elif deviation_rate > 15 or deviation_rate < -10:
        neg += 1

    stock["resonance_positive_count"] = pos
    stock["resonance_negative_count"] = neg

    # 风险评分
    risk = 50
    if bearish_aligned:
        risk += 10
    elif bullish_aligned:
        risk -= 10

    if price_position > 0.70:
        risk += 5
    elif price_position < 0.25:
        risk -= 3

    if deviation_rate > 10:
        risk += 5
    elif deviation_rate > 6:
        risk += 2

    if change_pct < -1 and volume_ratio > 1.5:
        risk += 8
    elif change_pct < -2 and volume_ratio > 1.2:
        risk += 5

    if change_pct < 0:
        risk += 3
    elif change_pct > 3:
        risk -= 3

    if change_pct_3d > 8:
        risk += 5
    elif change_pct_3d > 5:
        risk += 2

    stock["risk_score"] = max(0, min(100, round(risk)))

    # 反转判定
    stock["_is_reversal_by_formula"] = _check_reversal_by_formula(stock)

    return stock


# ═══════════════════════════════════════════════════
# 五层流水线执行
# ═══════════════════════════════════════════════════

def _apply_layer1(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """第1层：快速底层过滤"""
    filters = [
        filter_not_st,
        filter_not_suspended,
        partial(filter_min_price, min_p=1.0),
        filter_not_new_share,
    ]
    result = []
    for s in stocks:
        try:
            if all(f(s) for f in filters):
                result.append(s)
        except Exception as e:
            logger.warning(f"L1异常 [{s.get('code', '?')}]: {e}")
    logger.debug(f"L1底层过滤: {len(stocks)} -> {len(result)}")
    return result


def _apply_layer2_liquidity(stocks):
    """L2 liquidity filter"""
    result = []
    for s in stocks:
        try:
            if filter_liquidity(s):
                result.append(s)
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"L2 liq [{s.get('code', '?')}]: {e}")
    return result

def _apply_financial_filter(
    stocks: List[Dict[str, Any]],
    strategy: str,
) -> List[Dict[str, Any]]:
    """财务+事件过滤（前置，L1之后立即执行）"""
    fin_filters = _build_financial_filters(strategy)
    event_filters = _build_event_filters()

    result = []
    for s in stocks:
        try:
            # 财务条件（全部满足）
            fin_pass = all(f(s) for f in fin_filters)
            if not fin_pass:
                continue

            # 事件风险（全部满足）
            event_pass = all(f(s) for f in event_filters)
            if not event_pass:
                continue

            result.append(s)
        except Exception as e:
            logger.warning(f"财务/事件过滤异常 [{s.get('code', '?')}]: {e}")

    logger.debug(f"财务+事件过滤 [{strategy}]: {len(stocks)} -> {len(result)}")
    return result


def _apply_layer2(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """第2层：轻量技术指标（全部6项满足）"""
    filters = L2_ALL_FILTERS
    result = []
    fail_counts = {}
    for s in stocks:
        try:
            passed = all(f(s) for f in filters)
            if passed:
                result.append(s)
            else:
                # 统计哪些条件失败
                for idx, f in enumerate(filters):
                    if not f(s):
                        fn = f.__name__
                        fail_counts[fn] = fail_counts.get(fn, 0) + 1
                        break
        except Exception as e:
            logger.warning(f"L2异常 [{s.get('code', '?')}]: {e}")

    if fail_counts:
        top_fails = sorted(fail_counts.items(), key=lambda x: -x[1])[:3]
        logger.debug(f"L2技术面(全部6项): {len(stocks)} -> {len(result)} "
                     f"失败率前3: {[(k, v) for k, v in top_fails]}")
    else:
        logger.debug(f"L2技术面(全部6项): {len(stocks)} -> {len(result)}")
    return result


def _apply_layer3(
    stocks: List[Dict[str, Any]],
    strategy: str,
    batch_processor: BatchProcessor,
) -> List[Dict[str, Any]]:
    """
    第3层：深度技术面精筛。
    
    强制：趋势方向上涨/反转 + 多头共振≥4 + 风险≤40
    附加项至少2项（方案替换规则：量比≥1.5可少1项）
    剔除条件（任意1项直接剔除）
    """
    result = []
    mandatory_fail = 0
    optional_fail = 0
    exclusion_fail = 0

    for s in stocks:
        try:
            # 强制条件（全部满足）
            if not l3_trend_up_or_reversal(s):
                mandatory_fail += 1
                continue
            if not l3_resonance_ge_4(s):
                mandatory_fail += 1
                continue
            if not l3_risk_le_40(s):
                mandatory_fail += 1
                continue

            # 方案替换规则：量比≥1.5可替换任意1项
            min_opt = 2
            if strategy in ("reversal_breakout", "short_term_strong"):
                if l3_volume_ratio_ge_1_5(s):
                    min_opt = max(0, min_opt - 1)

            # 附加项（至少满足min_opt项）
            opt_matches = sum(1 for f in L3_OPTIONAL_FILTERS if f(s))
            if opt_matches < min_opt:
                optional_fail += 1
                continue

            # 剔除条件（任意1项直接剔除）
            excluded = False
            for f in L3_EXCLUSION_FILTERS:
                if f(s):
                    excluded = True
                    exclusion_fail += 1
                    break

            if not excluded:
                s["_l3_opt_match"] = opt_matches
                result.append(s)
        except Exception as e:
            logger.warning(f"L3异常 [{s.get('code', '?')}]: {e}")

    logger.info(
        f"L3深度技术精筛 [{strategy}]: {len(stocks)} -> {len(result)} "
        f"(强制失败={mandatory_fail}, 附加不足={optional_fail}, 剔除={exclusion_fail})"
    )
    return result


# ═══════════════════════════════════════════════════
# 主入口函数
# ═══════════════════════════════════════════════════

def fixed_selection(
    template_id: str,
    all_stocks: List[Dict[str, Any]],
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    固定规则选股（v3.0 五层漏斗）。

    Args:
        template_id: 策略模板ID
        all_stocks: 全A股股票列表
        max_results: 最大输出数量，默认20，范围1-100

    Returns:
        {"template": ..., "layer_counts": ..., "results": [...], "count": int}
    """
    # 解析策略ID
    TEMPLATE_ID_MAP = {
        "stable_trend": "steady_trend",
        "reversal_breakthrough": "reversal_breakout",
    }
    resolved_id = TEMPLATE_ID_MAP.get(template_id, template_id)
    valid_strategies = ["steady_trend", "reversal_breakout", "short_term_strong"]
    if resolved_id not in valid_strategies:
        raise ValueError(f"未知模板ID: {template_id}")

    # 策略配置
    STRATEGY_CONFIG = {
        "steady_trend": {"name": "稳健趋势型", "max": 20},
        "reversal_breakout": {"name": "反转突破型", "max": 20},
        "short_term_strong": {"name": "短线强势型", "max": 20},
    }
    strategy = resolved_id
    config = STRATEGY_CONFIG[strategy]
    capacity = max(1, min(100, max_results if max_results is not None else config["max"]))

    logger.info(f"固定选股 [{config['name']}]: 开始，总池={len(all_stocks)}, 容量={capacity}")

    # 分批处理器
    batch_processor = BatchProcessor(batch_size=200, sleep_seconds=0.1)

    layer_counts = {}

    # ── L1：快速底层过滤 ──
    l1_stocks = _apply_layer1(all_stocks)
    layer_counts["layer1"] = len(l1_stocks)
    logger.info(f"L1: {len(all_stocks)} -> {len(l1_stocks)}")

    # ── 财务+事件过滤（前置）──
    l1_stocks = _apply_financial_filter(l1_stocks, strategy)
    layer_counts["layer2"] = len(l1_stocks)
    logger.info(f"FIN: (前置) -> {len(l1_stocks)}")
    l1_stocks = _apply_layer2_liquidity(l1_stocks)
    layer_counts["layer3"] = len(l1_stocks)
    logger.info(f"L3\u6d41\u52a8\u6027: {len(l1_stocks)}")

    # ── L2：轻量技术指标（全部6项）──
    l4_stocks = _apply_layer2(l1_stocks)
    layer_counts["layer4"] = len(l4_stocks)
    logger.info(f"L3: {len(l1_stocks)} -> {len(l4_stocks)}")

    # ── L3：深度技术面精筛（含技术指标富集）──
    # 先进行技术指标富集（分批处理）
    l4_enriched = batch_processor.process_with_enrich(
        l4_stocks,
        filter_func=lambda s: True,  # 先不过滤，只富集
        enrich_func=_enrich_technicals,
    )
    l5_stocks = _apply_layer3(l4_enriched, strategy, batch_processor)
    layer_counts["layer5"] = len(l5_stocks)

    # ── L4：综合评分、输出分级、容量控制 ──
    # 评分并排序（≥70分保留，≥85优质标的，≥90核心精选）
    scored = sort_by_score(l5_stocks, top_n=capacity * 2, strategy=strategy)

    # 分级过滤：<70排除，70-84稳健关注(不进推荐)，≥85优质标的/核心精选
    # 但均返回给前端（前端根据 grade 字段展示不同级别）
    results = [s for s in scored if s.get("total_score", 0) >= 70]
    results = results[:capacity]

    layer_counts["layer6_scored"] = len(results)
    grade_counts = {"核心精选": 0, "优质标的": 0, "稳健关注": 0}
    for s in results:
        g = s.get("grade", "")
        if g in grade_counts:
            grade_counts[g] += 1

    logger.info(
        f"固定选股 [{config['name']}](容量={capacity}): "
        f"L1={layer_counts['layer1']} L2={layer_counts['layer2']} L3={layer_counts['layer3']} L4={layer_counts['layer4']} L5={layer_counts['layer5']} L6\u8bc4\u5206={layer_counts['layer6_scored']}"f"L1={layer_counts['layer1']} L2={layer_counts['layer2']} "
        f"L2={layer_counts['layer2']} L3={layer_counts['layer3']} "
        f"L5评分={layer_counts['layer6_scored']} "
        f"分级={grade_counts}"
    )

    return {
        "template": {
            "id": strategy,
            "name": config["name"],
            "description": "",
            "max_results": capacity,
        },
        "total_count": len(all_stocks),
        "layer_counts": layer_counts,
        "grade_counts": grade_counts,
        "results": results,
        "count": len(results),
    }


# Fixed selection templates config (for main.py)
SELECTION_TEMPLATES = {
    "steady_trend": {"id": "steady_trend", "name": "稳健趋势型", "strategy": "conservative"},
    "reversal_breakout": {"id": "reversal_breakout", "name": "反转突破型", "strategy": "reversal"},
    "short_term_strong": {"id": "short_term_strong", "name": "短线强势型", "strategy": "aggressive"},
}
