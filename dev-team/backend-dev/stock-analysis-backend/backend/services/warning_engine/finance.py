"""
M03 预警计算引擎 — 财务预警模块（按设计文档完全重写）

规则来源：6.智能预警模块.md §3.5 财务预警

异常指标（10项）：
1. 最近1年净利润为负，或连续2年扣非净利润为负
2. 扣非净利润/净利润 < 0.3（扣非净利>1亿则放宽至<0.2）
3. 资产负债率 > 行业均值×1.2 或 行业分位数>80%
4. 有息负债/净资产 > 1.5
5. 经营现金流为负且连续2年恶化
6. 销售收现/营收 < 0.8
7. 营收同比增速 < -20%
8. （应收增速-营收增速）>20% 或 （存货增速-营收增速）>20%
9. 审计非标/信披违规/立案调查/高质押爆仓风险
10. 净资产为负或大幅下滑>50%

分级：🟢无异常 🟡1项异常 🔴2-3项异常 ⚫≥4项或强制规避

更新频率：每日开盘前加载一次，交易日期间不实时变化。
"""

from typing import Optional, Dict, Any, List
import json
import logging

from backend.services.warning_engine.price import WarningResult

logger = logging.getLogger(__name__)


def check_finance_warning(
    code: str,
    name: str,
    price: float = 0,
    pe: Optional[float] = None,
    pb: Optional[float] = None,
    roe: Optional[float] = None,
    revenue_growth: Optional[float] = None,
    profit_growth: Optional[float] = None,
    debt_ratio: Optional[float] = None,
    thresholds: Dict[str, Any] = None,
    **kwargs,
) -> Optional[WarningResult]:
    """
    按设计文档6.3.5节计算财务预警。

    检查10项异常指标，返回异常计数+强制规避标记。
    每日开盘前计算一次，交易日期间不变化。
    
    kwargs 可传入：
    - net_profit_negative: bool 最近1年净利润为负
    - deducted_profit_negative: bool 连续2年扣非净利润为负
    - deducted_profit_ratio: float 扣非净利润/净利润
    - deducted_profit_amount: float 扣非净利润金额(亿)
    - debt_ratio: float 资产负债率(%)
    - industry_avg_debt: float 行业平均资产负债率(%)
    - interest_debt_ratio: float 有息负债/净资产
    - operating_cashflow_negative: bool 经营现金流为负
    - cashflow_worsening: bool 连续2年恶化
    - revenue_growth_high: bool 营收增速>30%
    - market_cap_small: bool 市值<100亿
    - cash_receipt_ratio: float 销售收现/营收
    - revenue_growth_finance: float 营收同比增速(%)
    - receivables_growth: float 应收增速(%)
    - inventory_growth: float 存货增速(%)
    - audit_modified: bool 保留/否定/无法表示意见
    - info_violation: bool 重大信披违规/立案调查
    - pledge_risk: bool 大股东高比例质押爆仓风险
    - net_asset_negative: bool 净资产为负
    - net_asset_decline_50: bool 净资产同比降幅>50%
    - hard_fraud: bool 财务造假+退市标准
    - hard_debt_default: bool 债务违约/展期
    - hard_pledge_force: bool 质押违约/强平
    - hard_net_asset_negative: bool 净资产为负
    """
    # 收集异常项
    anomalies = []
    hard_avoid = False

    # 1. 最近1年净利润为负，或连续2年扣非净利润为负
    if kwargs.get("net_profit_negative") or kwargs.get("deducted_profit_negative"):
        anomalies.append("净利润为负/扣非净利润连续为负")

    # 2. 扣非净利润/净利润 < 0.3
    dpr = kwargs.get("deducted_profit_ratio")
    das = kwargs.get("deducted_profit_amount", 0) or 0
    if dpr is not None:
        threshold = 0.2 if das > 1 else 0.3
        if dpr < threshold:
            anomalies.append(f"扣非净利/净利={dpr:.2f}＜{threshold}")

    # 3. 资产负债率 > 行业均值×1.2 或 行业分位数>80%
    dr = kwargs.get("debt_ratio", debt_ratio)
    iad = kwargs.get("industry_avg_debt")
    if dr is not None:
        if iad and dr > iad * 1.2:
            anomalies.append(f"资产负债率{dr:.0f}%＞行业均值×1.2")
        elif not iad and dr > 85:
            anomalies.append(f"资产负债率{dr:.0f}%＞85%")

    # 4. 有息负债/净资产 > 1.5
    idr = kwargs.get("interest_debt_ratio")
    if idr is not None and idr > 1.5:
        anomalies.append(f"有息负债/净资产={idr:.2f}＞1.5")

    # 5. 经营现金流为负且连续2年恶化
    oc_neg = kwargs.get("operating_cashflow_negative")
    cf_worse = kwargs.get("cashflow_worsening")
    rg_high = kwargs.get("revenue_growth_high")
    mc_small = kwargs.get("market_cap_small")
    if oc_neg and cf_worse:
        # 放宽条件：营收增速>30%且市值<100亿，则不计数
        if not (rg_high and mc_small):
            anomalies.append("经营现金流为负且连续恶化")

    # 6. 销售收现/营收 < 0.8
    crr = kwargs.get("cash_receipt_ratio")
    if crr is not None and crr < 0.8:
        anomalies.append(f"销售收现/营收={crr:.2f}＜0.8")

    # 7. 营收同比增速 < -20%
    rg = kwargs.get("revenue_growth_finance", revenue_growth)
    if rg is not None and rg < -20:
        anomalies.append(f"营收同比增速={rg:.1f}%＜-20%")

    # 8. （应收增速−营收增速）>20% 或 （存货增速−营收增速）>20%
    rec_g = kwargs.get("receivables_growth")
    inv_g = kwargs.get("inventory_growth")
    rg_fin = kwargs.get("revenue_growth_finance", revenue_growth)
    if rec_g is not None and rg_fin is not None:
        if rec_g - rg_fin > 20:
            anomalies.append(f"应收增速-营收增速={rec_g-rg_fin:.0f}%＞20%")
    if inv_g is not None and rg_fin is not None:
        if inv_g - rg_fin > 20:
            anomalies.append(f"存货增速-营收增速={inv_g-rg_fin:.0f}%＞20%")

    # 9. 审计非标/信披违规/立案调查/高质押爆仓
    audit = kwargs.get("audit_modified")
    violation = kwargs.get("info_violation")
    pledge = kwargs.get("pledge_risk")
    if audit:
        anomalies.append("审计非标/否定/无法表示意见")
    if violation:
        anomalies.append("重大信披违规/立案调查")
    if pledge:
        anomalies.append("高质押爆仓风险")

    # 10. 净资产为负或大幅下滑>50%
    na_neg = kwargs.get("net_asset_negative")
    na_decline = kwargs.get("net_asset_decline_50")
    if na_neg or na_decline:
        anomalies.append("净资产为负或大幅下滑>50%")

    # ── 强制规避项 ──
    if kwargs.get("hard_fraud"):
        hard_avoid = True
        anomalies.append("财务造假+退市标准")
    if kwargs.get("hard_debt_default"):
        hard_avoid = True
        anomalies.append("债务违约/展期")
    if kwargs.get("hard_pledge_force"):
        hard_avoid = True
        anomalies.append("质押违约/强平")
    if kwargs.get("hard_net_asset_negative") or na_neg:
        hard_avoid = True
        if "净资产为负或大幅下滑>50%" not in anomalies:
            anomalies.append("净资产为负")

    # ── 确定颜色 ──
    anomaly_count = len(anomalies)
    if hard_avoid or anomaly_count >= 4:
        color = "black"
        level = "critical"
    elif anomaly_count >= 2:
        color = "red"
        level = "danger"
    elif anomaly_count == 1:
        color = "yellow"
        level = "warning"
    else:
        color = "green"
        level = "info"

    detail = {
        "code": code,
        "name": name,
        "anomaly_count": anomaly_count,
        "hard_avoid": hard_avoid,
        "anomalies": anomalies,
    }

    if anomaly_count > 0:
        title = f"{name}({code}) {anomaly_count}项异常【{'; '.join(anomalies[:3])}】"
    else:
        title = f"{name}({code}) 财务正常"

    return WarningResult(
        code=code, warning_type="finance",
        warning_level=level, title=title,
        detail=str(detail),
        indicator_color=color,
        triggered=color not in ("green",),
    )
