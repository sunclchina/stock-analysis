"""
M04 选股引擎 — 自定义选股（v3.0 四步筛选）。

设计文档 §6.2 筛选顺序重排：
Step 1 范围筛选：行业/市值/上市时间/流动性 → <1000只
Step 2 基本面筛选：预加载数据 → <500只
Step 3 技术面筛选：均线/MACD/KDJ/RSI/量比/趋势
Step 4 共振类筛选：低位/高位/多指标共振

结果限制熔断：中间结果>1000停止、单次>8秒超时、结果>500提示
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from backend.services.selection_engine.scorer import sort_by_score
from backend.services.selection_engine.financial_cache import financial_data_loader
from backend.services.selection_engine.fixed import _enrich_technicals

logger = logging.getLogger(__name__)

# ─── 限制常量 ──────────────────────────────────────

MAX_INTERMEDIATE = 1000       # 中间结果熔断阈值
MAX_FINAL_RESULTS = 500       # 最终结果硬上限
TIMEOUT_SECONDS = 8           # 单次超时
STEP_LIMITS = {
    "scope": 1000,            # Step1: <1000
    "fundamental": 500,       # Step2: <500
}


# ─── 辅助函数 ──────────────────────────────────────

def _safe_float(val, default=None) -> Optional[float]:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _safe_int(val, default=None) -> Optional[int]:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════
# Step 1: 范围筛选
# ═══════════════════════════════════════════════════

def _build_scope_filters(scope: Dict[str, Any], logic: str = "and") -> List[Callable]:
    """构建范围筛选过滤函数"""
    filters = []

    # 行业筛选
    industries = scope.get("industries")
    if industries and isinstance(industries, list) and len(industries) > 0:
        ind_set = set(i.strip() for i in industries if i.strip())
        if ind_set:
            def _industry_filter(stock, ids=ind_set):
                ind = (stock.get("industry") or "")
                if not ind:
                    return False
                if ind in ids:
                    return True
                for uid in ids:
                    if uid in ind or ind in uid:
                        return True
                return False
            filters.append(_industry_filter)

    # 总市值区间（流通市值近似）
    market_cap = scope.get("market_cap")
    if market_cap and isinstance(market_cap, dict):
        mc_min = _safe_float(market_cap.get("min"))
        mc_max = _safe_float(market_cap.get("max"))
        if mc_min is not None or mc_max is not None:
            def _market_cap_filter(stock, mn=mc_min, mx=mc_max):
                mc = _safe_float(stock.get("circ_market_value"))
                if mc is None or mc <= 0:
                    return True  # 无数据跳过
                if mn is not None and mc < mn:
                    return False
                if mx is not None and mc > mx:
                    return False
                return True
            filters.append(_market_cap_filter)

    # 上市时间
    listing_days = scope.get("listing_days")
    if listing_days is not None:
        try:
            min_days = int(listing_days)
            def _listing_days_filter(stock, md=min_days):
                td = stock.get("trade_days_since_listing")
                if td is None:
                    return True
                return int(td) >= md
            filters.append(_listing_days_filter)
        except (ValueError, TypeError):
            pass

    # 流动性（成交额）
    amount_cond = scope.get("amount")
    if amount_cond and isinstance(amount_cond, dict):
        amt_min = _safe_float(amount_cond.get("min"))
        amt_max = _safe_float(amount_cond.get("max"))
        if amt_min is not None or amt_max is not None:
            def _amount_filter(stock, mn=amt_min, mx=amt_max):
                amt = _safe_float(stock.get("amount"))
                if amt is None:
                    return False
                if mn is not None and amt < mn:
                    return False
                if mx is not None and amt > mx:
                    return False
                return True
            filters.append(_amount_filter)

    # 股价范围
    price_cond = scope.get("price")
    if price_cond and isinstance(price_cond, dict):
        p_min = _safe_float(price_cond.get("min"))
        p_max = _safe_float(price_cond.get("max"))
        if p_min is not None or p_max is not None:
            def _price_filter(stock, mn=p_min, mx=p_max):
                pr = _safe_float(stock.get("price"))
                if pr is None:
                    return False
                if mn is not None and pr < mn:
                    return False
                if mx is not None and pr > mx:
                    return False
                return True
            filters.append(_price_filter)

    return filters


# ═══════════════════════════════════════════════════
# Step 2: 基本面筛选（使用预加载数据）
# ═══════════════════════════════════════════════════

def _build_fundamental_filters(fund: Dict[str, Any], logic: str = "and") -> List[Callable]:
    """构建基本面筛选过滤函数"""
    filters = []

    # 净利润增长率
    pg_cond = fund.get("profit_growth")
    if pg_cond and isinstance(pg_cond, dict):
        pg_min = _safe_float(pg_cond.get("min"))
        pg_max = _safe_float(pg_cond.get("max"))
        if pg_min is not None or pg_max is not None:
            def _profit_growth_filter(stock, mn=pg_min, mx=pg_max):
                pg = _safe_float(stock.get("profit_growth")) or _safe_float(stock.get("net_profit_growth"))
                if pg is None:
                    return False
                if mn is not None and pg < mn:
                    return False
                if mx is not None and pg > mx:
                    return False
                return True
            filters.append(_profit_growth_filter)

    # 资产负债率
    dr_cond = fund.get("debt_ratio")
    if dr_cond and isinstance(dr_cond, dict):
        dr_min = _safe_float(dr_cond.get("min"))
        dr_max = _safe_float(dr_cond.get("max"))
        if dr_min is not None or dr_max is not None:
            def _debt_ratio_filter(stock, mn=dr_min, mx=dr_max):
                dr = _safe_float(stock.get("debt_ratio"))
                if dr is None:
                    return False
                if mn is not None and dr < mn:
                    return False
                if mx is not None and dr > mx:
                    return False
                return True
            filters.append(_debt_ratio_filter)

    # 市盈率
    pe_cond = fund.get("pe")
    if pe_cond and isinstance(pe_cond, dict):
        pe_min = _safe_float(pe_cond.get("min"))
        pe_max = _safe_float(pe_cond.get("max"))
        if pe_min is not None or pe_max is not None:
            def _pe_filter(stock, mn=pe_min, mx=pe_max):
                pe = _safe_float(stock.get("pe"))
                if pe is None or pe <= 0:
                    return True
                if mn is not None and pe < mn:
                    return False
                if mx is not None and pe > mx:
                    return False
                return True
            filters.append(_pe_filter)

    # 市净率
    pb_cond = fund.get("pb")
    if pb_cond and isinstance(pb_cond, dict):
        pb_min = _safe_float(pb_cond.get("min"))
        pb_max = _safe_float(pb_cond.get("max"))
        if pb_min is not None or pb_max is not None:
            def _pb_filter(stock, mn=pb_min, mx=pb_max):
                pb = _safe_float(stock.get("pb"))
                if pb is None or pb <= 0:
                    return True
                if mn is not None and pb < mn:
                    return False
                if mx is not None and pb > mx:
                    return False
                return True
            filters.append(_pb_filter)

    # ROE
    roe_cond = fund.get("roe")
    if roe_cond and isinstance(roe_cond, dict):
        roe_min = _safe_float(roe_cond.get("min"))
        if roe_min is not None:
            def _roe_filter(stock, mn=roe_min):
                roe = _safe_float(stock.get("roe"))
                if roe is None:
                    return False
                return roe >= mn
            filters.append(_roe_filter)

    # 毛利率
    gm_cond = fund.get("gross_margin")
    if gm_cond and isinstance(gm_cond, dict):
        gm_min = _safe_float(gm_cond.get("min"))
        gm_max = _safe_float(gm_cond.get("max"))
        if gm_min is not None or gm_max is not None:
            def _gross_margin_filter(stock, mn=gm_min, mx=gm_max):
                gm = _safe_float(stock.get("gross_margin"))
                if gm is None:
                    return False
                if mn is not None and gm < mn:
                    return False
                if mx is not None and gm > mx:
                    return False
                return True
            filters.append(_gross_margin_filter)

    # 经营现金流>0
    cashflow_positive = fund.get("operate_cashflow_positive")
    if cashflow_positive:
        def _cashflow_filter(stock):
            cf = _safe_float(stock.get("operate_cashflow"))
            if cf is None:
                return False
            return cf > 0
        filters.append(_cashflow_filter)

    # 财务等级联动
    finance_grade = fund.get("finance_grade")
    if finance_grade:
        valid_grades = set()
        val = str(finance_grade).lower()
        if val in ("green", "🟢", "safe", "a"):
            valid_grades = {"green", "a", "safe"}
        elif val in ("yellow", "b"):
            valid_grades = {"green", "yellow", "b", "safe"}
        elif val in ("red", "c", "d"):
            valid_grades = {"green", "yellow", "red", "c", "d"}
        if valid_grades:
            def _finance_grade_filter(stock, vg=valid_grades):
                fg = stock.get("finance_grade", stock.get("finance_color", ""))
                if fg is None:
                    fg = ""
                return str(fg).lower() in vg
            filters.append(_finance_grade_filter)

    # 财务预警排除
    if fund.get("exclude_warning", False):
        def _exclude_warn_filter(stock):
            grade = stock.get("finance_grade", stock.get("finance_color", ""))
            if isinstance(grade, str):
                return grade.lower() not in ("red", "black", "d", "f")
            return True
        filters.append(_exclude_warn_filter)

    return filters


# ═══════════════════════════════════════════════════
# Step 3: 技术面筛选
# ═══════════════════════════════════════════════════

def _build_technical_filters(tech: Dict[str, Any]) -> List[Callable]:
    """构建技术面筛选过滤函数"""
    filters = []

    # 均线排列
    ma_type = tech.get("ma_type")
    if ma_type:
        ma_type = str(ma_type).lower()
        if ma_type == "bullish":
            def _ma_bullish(stock):
                m5 = _safe_float(stock.get("ma5"))
                m10 = _safe_float(stock.get("ma10"))
                m20 = _safe_float(stock.get("ma20"))
                if any(v is None for v in (m5, m10, m20)):
                    return False
                return m5 > m10 > m20
            filters.append(_ma_bullish)
        elif ma_type == "bearish":
            def _ma_bearish(stock):
                m5 = _safe_float(stock.get("ma5"))
                m10 = _safe_float(stock.get("ma10"))
                m20 = _safe_float(stock.get("ma20"))
                if any(v is None for v in (m5, m10, m20)):
                    return False
                return m5 < m10 < m20
            filters.append(_ma_bearish)
        elif ma_type == "entanglement":
            def _ma_entanglement(stock):
                m5 = _safe_float(stock.get("ma5"))
                m10 = _safe_float(stock.get("ma10"))
                m20 = _safe_float(stock.get("ma20"))
                pr = _safe_float(stock.get("price"))
                if any(v is None for v in (m5, m10, m20, pr)):
                    return False
                if m5 > m10 > m20:
                    return False
                if m5 < m10 < m20:
                    return False
                return abs(pr - m20) / m20 <= 0.05
            filters.append(_ma_entanglement)

    # 价格与MA关系
    price_above_ma = tech.get("price_above_ma")
    if price_above_ma:
        pa = str(price_above_ma).lower()
        if pa == "ma5":
            def _p_above_ma5(stock):
                p = _safe_float(stock.get("price"))
                m5 = _safe_float(stock.get("ma5"))
                if p is None or m5 is None:
                    return False
                return p > m5
            filters.append(_p_above_ma5)
        elif pa == "ma10":
            def _p_above_ma10(stock):
                p = _safe_float(stock.get("price"))
                m10 = _safe_float(stock.get("ma10"))
                if p is None or m10 is None:
                    return False
                return p > m10
            filters.append(_p_above_ma10)
        elif pa == "ma20":
            def _p_above_ma20(stock):
                p = _safe_float(stock.get("price"))
                m20 = _safe_float(stock.get("ma20"))
                if p is None or m20 is None:
                    return False
                return p > m20
            filters.append(_p_above_ma20)

    # MACD状态
    macd_state = tech.get("macd_state")
    if macd_state and isinstance(macd_state, list) and len(macd_state) > 0:
        state_set = set(str(s).lower() for s in macd_state)
        checks = []
        if "golden" in state_set:
            def _macd_golden(stock):
                sig = stock.get("macd_signal")
                if not sig:
                    return True
                return sig == "golden"
            checks.append(_macd_golden)
        if "death" in state_set:
            def _macd_death(stock):
                sig = stock.get("macd_signal")
                if not sig:
                    return True
                return sig == "death"
            checks.append(_macd_death)
        if "red_expand" in state_set:
            def _macd_red(stock):
                bar = _safe_float(stock.get("macd_bar"))
                if bar is None:
                    return False
                return bar > 0
            checks.append(_macd_red)
        if checks:
            def _macd_or(stock, ch=checks):
                return any(f(stock) for f in ch)
            filters.append(_macd_or)

    # 量比区间
    vr_cond = tech.get("volume_ratio")
    if vr_cond and isinstance(vr_cond, dict):
        vr_min = _safe_float(vr_cond.get("min"))
        vr_max = _safe_float(vr_cond.get("max"))
        if vr_min is not None or vr_max is not None:
            def _vr_filter(stock, mn=vr_min, mx=vr_max):
                vr = _safe_float(stock.get("volume_ratio"))
                if vr is None or vr <= 0:
                    return True
                if mn is not None and vr < mn:
                    return False
                if mx is not None and vr > mx:
                    return False
                return True
            filters.append(_vr_filter)

    # 换手率区间
    tr_cond = tech.get("turnover_rate")
    if tr_cond and isinstance(tr_cond, dict):
        tr_min = _safe_float(tr_cond.get("min"))
        tr_max = _safe_float(tr_cond.get("max"))
        if tr_min is not None or tr_max is not None:
            def _tr_filter(stock, mn=tr_min, mx=tr_max):
                tr = stock.get("turnover_rate")
                if tr is None:
                    # 数据缺失时放过（尽力而为模式，不为难用户）
                    return True
                tr = _safe_float(tr)
                if tr is None:
                    return True
                if mn is not None and tr < mn:
                    return False
                if mx is not None and tr > mx:
                    return False
                return True
            filters.append(_tr_filter)

    # RSI条件
    rsi_state = tech.get("rsi_state")
    if rsi_state:
        rs = str(rsi_state).lower()
        if rs == "gt_70":
            def _rsi_gt70(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r > 70
            filters.append(_rsi_gt70)
        elif rs == "lt_30":
            def _rsi_lt30(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r < 30
            filters.append(_rsi_lt30)
        elif rs == "gt_50":
            def _rsi_gt50(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r > 50
            filters.append(_rsi_gt50)
        elif rs == "lt_50":
            def _rsi_lt50(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r < 50
            filters.append(_rsi_lt50)

    # 布林带位置
    boll_pos = tech.get("bollinger_position")
    if boll_pos:
        bp = str(boll_pos).lower()
        if bp == "upper":
            def _boll_upper(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev >= 6.0
            filters.append(_boll_upper)
        elif bp == "middle":
            def _boll_middle(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return -2.0 <= dev <= 2.0
            filters.append(_boll_middle)
        elif bp == "lower":
            def _boll_lower(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev <= -6.0
            filters.append(_boll_lower)
        elif bp == "below":
            def _boll_below(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev < -2.0
            filters.append(_boll_below)

    # 趋势方向
    trend = tech.get("trend_direction")
    if trend:
        td = str(trend).lower()
        if td in ("up", "bullish"):
            def _trend_up(stock):
                d = stock.get("trend_direction", "")
                return d in ("bullish", "up", "reversal", "bullish_reversal")
            filters.append(_trend_up)
        elif td in ("down", "bearish"):
            def _trend_down(stock):
                d = stock.get("trend_direction", "")
                return d == "bearish"
            filters.append(_trend_down)

    return filters


# ═══════════════════════════════════════════════════
# Step 4: 共振类筛选
# ═══════════════════════════════════════════════════

def _build_resonance_filters(resonance: Dict[str, Any]) -> List[Callable]:
    """构建共振类筛选过滤函数"""
    filters = []

    # 低位共振条件
    low_cond_list = resonance.get("low_resonance")
    if low_cond_list and isinstance(low_cond_list, list) and len(low_cond_list) > 0:
        low_checks = _resonance_checks(low_cond_list, "low")
        if low_checks:
            def _low_resonance(stock, ch=low_checks):
                return any(f(stock) for f in ch)
            filters.append(_low_resonance)

    # 高位共振条件
    high_cond_list = resonance.get("high_resonance")
    if high_cond_list and isinstance(high_cond_list, list) and len(high_cond_list) > 0:
        high_checks = _resonance_checks(high_cond_list, "high")
        if high_checks:
            def _high_resonance(stock, ch=high_checks):
                return any(f(stock) for f in ch)
            filters.append(_high_resonance)

    # 多指标共振
    multi_cond_list = resonance.get("multi_resonance")
    min_match = resonance.get("min_match", 1)
    if multi_cond_list and isinstance(multi_cond_list, list) and len(multi_cond_list) > 0:
        multi_checks = _resonance_checks(multi_cond_list, "multi")
        if multi_checks:
            actual_min = max(1, min(min_match, len(multi_checks)))
            def _multi_resonance(stock, ch=multi_checks, need=actual_min):
                return sum(1 for f in ch if f(stock)) >= need
            filters.append(_multi_resonance)

    # 联动固定规则选股的共振体系
    if resonance.get("link_fixed_rules"):
        def _link_fixed(stock):
            direction = stock.get("trend_direction", "")
            if direction not in ("bullish", "up", "reversal", "bullish_reversal"):
                return False
            res_pos = stock.get("resonance_positive_count")
            if res_pos is None:
                return False
            return int(res_pos) >= 4
        filters.append(_link_fixed)

    return filters


def _resonance_checks(cond_list: List[str], mode: str) -> List[Callable]:
    """构建共振条件检查函数列表"""
    checks = []
    for cond in cond_list:
        c = cond.lower().replace("-", "_").replace(" ", "_")

        # === 通用条件 ===
        if c in ("macd_golden", "macd金叉"):
            def _ch_macd_g(stock):
                sig = stock.get("macd_signal")
                return sig == "golden"
            checks.append(_ch_macd_g)

        elif c in ("ma_bullish", "均线多头排列"):
            def _ch_ma_bull(stock):
                m5 = _safe_float(stock.get("ma5"))
                m10 = _safe_float(stock.get("ma10"))
                m20 = _safe_float(stock.get("ma20"))
                if any(v is None for v in (m5, m10, m20)):
                    return False
                return m5 > m10 > m20
            checks.append(_ch_ma_bull)

        elif c in ("volume_expand", "放量", "量比≥1.2", "量比"):
            def _ch_vol_exp(stock):
                vr = _safe_float(stock.get("volume_ratio"))
                if vr is None:
                    return False
                return vr >= 1.2
            checks.append(_ch_vol_exp)

        elif c in ("rsi_gt_50", "rsi>50"):
            def _ch_rsi_gt50(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r > 50
            checks.append(_ch_rsi_gt50)

        elif c in ("price_above_ma20", "站稳ma20"):
            def _ch_p_above_m20(stock):
                p = _safe_float(stock.get("price"))
                m20 = _safe_float(stock.get("ma20"))
                if p is None or m20 is None:
                    return False
                return p > m20
            checks.append(_ch_p_above_m20)

        elif c in ("trend_up", "趋势向上"):
            def _ch_trend_up(stock):
                d = stock.get("trend_direction", "")
                return d in ("bullish", "up", "reversal", "bullish_reversal")
            checks.append(_ch_trend_up)

        elif c in ("price_position_30_70", "价位30%-70%"):
            def _ch_pos_mid(stock):
                pos = _safe_float(stock.get("price_position"))
                if pos is None:
                    return False
                return 0.30 <= pos <= 0.70
            checks.append(_ch_pos_mid)

        elif c in ("ma20_trend_up", "ma20趋势向上"):
            def _ch_ma20_up(stock):
                return stock.get("ma20_trend_up", False)
            checks.append(_ch_ma20_up)

        # === 低位共振条件 ===
        elif c in ("low_position", "相对低位<30%", "低位"):
            def _ch_pos_low(stock):
                pos = _safe_float(stock.get("price_position"))
                if pos is None:
                    return False
                return pos < 0.30
            checks.append(_ch_pos_low)

        elif c in ("rsi_lt_30", "rsi<30", "超卖"):
            def _ch_rsi_low(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r < 30
            checks.append(_ch_rsi_low)

        elif c in ("boll_lower", "布林下轨", "下轨"):
            def _ch_boll_low(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev <= -6.0
            checks.append(_ch_boll_low)

        elif c in ("bottom_break", "底部分型"):
            def _ch_bottom(stock):
                pos = _safe_float(stock.get("price_position"))
                vr = _safe_float(stock.get("volume_ratio"))
                if pos is None or vr is None:
                    return False
                return pos < 0.20 and vr >= 1.0
            checks.append(_ch_bottom)

        elif c in ("neg_deviation_gt_8", "负乖离>8%"):
            def _ch_neg_dev(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev <= -8.0
            checks.append(_ch_neg_dev)

        # === 高位共振条件 ===
        elif c in ("high_position", "相对高位>70%", "高位"):
            def _ch_pos_high(stock):
                pos = _safe_float(stock.get("price_position"))
                if pos is None:
                    return False
                return pos > 0.70
            checks.append(_ch_pos_high)

        elif c in ("rsi_gt_70", "rsi>70", "超买"):
            def _ch_rsi_high(stock):
                r = _safe_float(stock.get("rsi"))
                if r is None:
                    return False
                return r > 70
            checks.append(_ch_rsi_high)

        elif c in ("boll_upper", "布林上轨", "上轨"):
            def _ch_boll_high(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev >= 6.0
            checks.append(_ch_boll_high)

        elif c in ("top_break", "顶部分型"):
            def _ch_top(stock):
                pos = _safe_float(stock.get("price_position"))
                vr = _safe_float(stock.get("volume_ratio"))
                if pos is None or vr is None:
                    return False
                return pos > 0.70 and vr >= 1.5
            checks.append(_ch_top)

        elif c in ("pos_deviation_gt_8", "正乖离>8%"):
            def _ch_pos_dev(stock):
                dev = _safe_float(stock.get("deviation_rate"))
                if dev is None:
                    return False
                return dev >= 8.0
            checks.append(_ch_pos_dev)

    return checks


# ═══════════════════════════════════════════════════
# 条件验证
# ═══════════════════════════════════════════════════

def validate_dimensions(dimensions: Dict[str, Any]) -> List[str]:
    """验证四大维度请求参数"""
    errors = []
    valid_dimensions = {"scope", "fundamental", "technical", "resonance"}
    for dim_name in dimensions:
        if dim_name not in valid_dimensions:
            errors.append(f"未知维度: {dim_name}")
    return errors


def _apply_filters(
    stocks: List[Dict[str, Any]],
    filters: List[Callable],
    logic: str = "and",
    step_name: str = "",
) -> List[Dict[str, Any]]:
    """应用过滤函数列表"""
    if not filters:
        return stocks

    result = []
    for s in stocks:
        try:
            if logic == "or":
                if any(f(s) for f in filters):
                    result.append(s)
            else:
                if all(f(s) for f in filters):
                    result.append(s)
        except Exception as e:
            logger.debug(f"{step_name}过滤异常 [{s.get('code', '?')}]: {e}")

    return result


# ═══════════════════════════════════════════════════
# 主入口函数
# ═══════════════════════════════════════════════════

async def custom_selection(
    conditions: Dict[str, Any],
    all_stocks: List[Dict[str, Any]],
    max_results: int = 50,
    scorer_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    自定义选股（v3.0 四步筛选）。

    请求格式：
    {
        "dimensions": {
            "scope": { "industries": [...], "logic": "and" },
            "fundamental": { "profit_growth": {"min": 10}, "logic": "and" },
            "technical": { "ma_type": "bullish", "logic": "and" },
            "resonance": { "multi_resonance": [...], "min_match": 2, "logic": "and" }
        },
        "max_results": 50,
        "dimension_logic": "and"
    }

    Args:
        conditions: 用户配置的条件
        all_stocks: 全A股股票列表
        max_results: 最大返回数量
        scorer_weights: 评分权重（保留参数）

    Returns:
        { "conditions_valid": bool, "errors": [...], "truncated": bool,
          "step_counts": {...}, "results": [...], "count": int, "message": str }
    """
    start_time = time.time()

    # 1. 解析请求参数
    if isinstance(conditions, dict) and "dimensions" in conditions:
        dimensions = conditions["dimensions"]
    else:
        dimensions = conditions

    if isinstance(dimensions, dict) and not any(
        k in dimensions for k in ("scope", "fundamental", "technical", "resonance")
    ):
        dimensions = {"technical": dimensions}

    if not isinstance(dimensions, dict):
        return {
            "conditions_valid": False,
            "errors": ["dimensions must be an object"],
            "truncated": False,
            "step_counts": {},
            "results": [],
            "count": 0,
            "message": "参数格式错误",
        }

    # 2. 验证
    errors = validate_dimensions(dimensions)
    if errors:
        return {
            "conditions_valid": False,
            "errors": errors,
            "truncated": False,
            "step_counts": {},
            "results": [],
            "count": 0,
            "message": "参数验证失败",
        }

    # 3. 执行四步筛选
    step_counts: Dict[str, int] = {}
    passed = list(all_stocks)
    truncated = False
    messages = []

    # ── Step 1: 范围筛选 ──
    scope_config = dimensions.get("scope", {})
    if scope_config and isinstance(scope_config, dict):
        scope_filters = _build_scope_filters(scope_config)
        if scope_filters:
            logic = scope_config.get("logic", "and")
            passed = _apply_filters(passed, scope_filters, logic, "Scope")
            step_counts["scope"] = len(passed)
            logger.info(f"Step1 范围筛选: {step_counts['scope']} 只")

    # 熔断检查：>1000截断（不设 truncated，仅限制计算量）
    remaining = len(passed)
    if remaining > MAX_INTERMEDIATE:
        passed = passed[:MAX_INTERMEDIATE]
        messages.append(f"范围筛选结果{remaining}只，取前{MAX_INTERMEDIATE}只继续")
        logger.warning(f"熔断: 范围筛选结果{remaining}只 > {MAX_INTERMEDIATE}")

    # 超时检查
    if time.time() - start_time > TIMEOUT_SECONDS:
        messages.append("超时(范围筛选阶段)")
        return _timeout_result(passed, step_counts, messages, start_time)

    # ── Step 2: 基本面筛选（使用预加载数据）──
    # 先富集财务数据
    if financial_data_loader.is_loaded:
        passed = [financial_data_loader.enrich_stock(s) for s in passed]

    fund_config = dimensions.get("fundamental", {})
    if fund_config and isinstance(fund_config, dict):
        fund_filters = _build_fundamental_filters(fund_config)
        if fund_filters:
            logic = fund_config.get("logic", "and")
            passed = _apply_filters(passed, fund_filters, logic, "Fundamental")
            step_counts["fundamental"] = len(passed)
            logger.info(f"Step2 基本面筛选: {step_counts['fundamental']} 只")

    # 熔断检查：>1000截断（不设 truncated，仅限制计算量）
    remaining = len(passed)
    if remaining > MAX_INTERMEDIATE:
        passed = passed[:MAX_INTERMEDIATE]
        messages.append(f"基本面筛选结果{remaining}只，取前{MAX_INTERMEDIATE}只继续")
        logger.warning(f"熔断: 基本面筛选结果{remaining}只 > {MAX_INTERMEDIATE}")

    # 超时检查
    if time.time() - start_time > TIMEOUT_SECONDS:
        messages.append("超时(基本面筛选阶段)")
        return _timeout_result(passed, step_counts, messages, start_time)

    # ── Step 3: 技术面筛选（先富集技术指标）──
    # 技术指标富集（分批处理）
    from backend.services.selection_engine.batch_processor import batch_map
    passed = batch_map(passed, _enrich_technicals, batch_size=200, sleep_seconds=0.05)

    tech_config = dimensions.get("technical", {})
    if tech_config and isinstance(tech_config, dict):
        tech_filters = _build_technical_filters(tech_config)
        if tech_filters:
            logic = tech_config.get("logic", "and")
            passed = _apply_filters(passed, tech_filters, logic, "Technical")
            step_counts["technical"] = len(passed)
            logger.info(f"Step3 技术面筛选: {step_counts['technical']} 只")

    # 超时检查
    if time.time() - start_time > TIMEOUT_SECONDS:
        messages.append("超时(技术面筛选阶段)")
        return _timeout_result(passed, step_counts, messages, start_time)

    # ── Step 4: 共振类筛选 ──
    res_config = dimensions.get("resonance", {})
    if res_config and isinstance(res_config, dict):
        res_filters = _build_resonance_filters(res_config)
        if res_filters:
            logic = res_config.get("logic", "and")
            passed = _apply_filters(passed, res_filters, logic, "Resonance")
            step_counts["resonance"] = len(passed)
            logger.info(f"Step4 共振筛选: {step_counts['resonance']} 只")

    # 超时检查
    if time.time() - start_time > TIMEOUT_SECONDS:
        messages.append("超时(共振筛选阶段)")

    # 4. 结果限制：超过500只提示
    if len(passed) > MAX_FINAL_RESULTS:
        truncated = True
        messages.append(f"结果超过{MAX_FINAL_RESULTS}只，建议增加筛选条件")
        passed = passed[:MAX_FINAL_RESULTS]

    # 5. 评分排序
    scored = sort_by_score(passed, weights=scorer_weights,
                           top_n=min(max_results, MAX_FINAL_RESULTS))

    if len(scored) == 0:
        messages.append("当前条件未选出符合条件的股票")

    elapsed = time.time() - start_time
    message = "，".join(messages) if messages else f"完成: {len(scored)} 只"

    logger.info(
        f"自定义选股(四步): 耗时{elapsed:.2f}s, "
        f"步数={len(step_counts)}, 最终={len(scored)}, 截断={truncated}"
    )

    return {
        "conditions_valid": True,
        "errors": [],
        "truncated": truncated,
        "step_counts": step_counts,
        "results": scored,
        "count": len(scored),
        "message": message,
        "elapsed_seconds": round(elapsed, 2),
    }


def _timeout_result(
    stocks: List[Dict[str, Any]],
    step_counts: Dict[str, int],
    messages: List[str],
    start_time: float,
) -> Dict[str, Any]:
    """超时时返回当前已选结果"""
    elapsed = time.time() - start_time
    from backend.services.selection_engine.batch_processor import batch_map
    stocks = batch_map(stocks, _enrich_technicals, batch_size=200, sleep_seconds=0.05)
    scored = sort_by_score(stocks, top_n=50)

    logger.warning(f"自定义选股超时: {elapsed:.2f}s, 返回已有结果{len(scored)}只")
    return {
        "conditions_valid": True,
        "errors": [],
        "truncated": True,
        "step_counts": step_counts,
        "results": scored,
        "count": len(scored),
        "message": "超时返回部分结果",
        "elapsed_seconds": round(elapsed, 2),
    }
