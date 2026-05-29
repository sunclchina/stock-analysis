"""
M03 预警计算引擎 — 综合决策矩阵（按设计文档完全重写）

规则来源：6.智能预警模块.md §4 综合决策矩阵

优先级（1最高→8最低）：
1. 任意模块⚫ → ⚫ 坚决回避/清仓
2. 突发=🔴或财务=🔴 → 🔴 减仓/不建仓
3. 风险=🔴或⚫ → 🔴 减仓避险
4. 趋势=🔵+共振=🟢 → 🟢 加仓/买入
5. 趋势=🟢+共振=🟢+风险≤🟡 → 🟢 持仓/正常参与
6. 趋势=🟡或共振=🟡 → 🟡 观望/轻仓
7. 趋势=🔴或共振=🔴 → 🔴 减仓/离场
8. 默认 → 🟡 观望

非交易时段：用静态颜色代入，每1分钟重算→只在收盘后重算一次锁定。
"""

from typing import List, Dict, Any

from backend.services.warning_engine.price import WarningResult

COLOR_PRIORITY = {
    "gray": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4, "blue": 5, "black": 6,
}


def get_highest_color(warnings: List[WarningResult]) -> str:
    """获取最高优先级的颜色（兼容旧接口）"""
    if not warnings:
        return "gray"
    max_color = max(
        (w.indicator_color for w in warnings),
        key=lambda c: COLOR_PRIORITY.get(c, 0),
    )
    return max_color


def extract_score(warning: WarningResult) -> float:
    """从预警结果detail中提取数值评分（兼容旧接口）"""
    return 0


def compute_decision(
    code: str,
    name: str,
    stock_warnings: Dict[str, WarningResult],
    thresholds: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    按设计文档§4综合决策矩阵计算。

    8级优先级逐层匹配。
    """
    # 提取各模块颜色
    def color(wtype: str) -> str:
        w = stock_warnings.get(wtype)
        return w.indicator_color if w else "gray"

    price_c = color("price")
    updown_c = color("updown")
    trend_c = color("trend")
    resonance_c = color("resonance")
    finance_c = color("finance")
    event_c = color("event")
    risk_c = color("risk")

    all_colors = [price_c, updown_c, trend_c, resonance_c, finance_c, event_c, risk_c]

    # 按优先级判定
    combined_color = "gray"
    suggestion_cn = "观望"

    # 1. 任意模块⚫ → ⚫ 坚决回避/清仓
    if any(c == "black" for c in all_colors):
        combined_color = "black"
        suggestion_cn = "坚决回避/清仓"
    # 2. 突发=🔴 或 财务=🔴 → 🔴 减仓/不建仓
    elif event_c == "red" or finance_c == "red":
        combined_color = "red"
        suggestion_cn = "减仓/不建仓"
    # 3. 风险=🔴 或 ⚫ → 🔴 减仓避险
    elif risk_c in ("red", "black"):
        combined_color = "red"
        suggestion_cn = "减仓避险"
    # 4. 趋势=🔵 + 共振=🟢 → 🟢 加仓/买入
    elif trend_c == "blue" and resonance_c == "green":
        combined_color = "green"
        suggestion_cn = "加仓/买入"
    # 5. 趋势=🟢 + 共振=🟢 + 风险≤🟡 → 🟢 持仓/正常参与
    elif trend_c == "green" and resonance_c == "green" and risk_c in ("gray", "green", "yellow"):
        combined_color = "green"
        suggestion_cn = "持仓/正常参与"
    # 6. 趋势=🟡 或 共振=🟡 → 🟡 观望/轻仓
    elif trend_c == "yellow" or resonance_c == "yellow":
        combined_color = "yellow"
        suggestion_cn = "观望/轻仓"
    # 7. 趋势=🔴 或 共振=🔴 → 🔴 减仓/离场
    elif trend_c == "red" or resonance_c == "red":
        combined_color = "red"
        suggestion_cn = "减仓/离场"
    # 8. 默认 → 🟡 观望
    else:
        combined_color = "yellow"
        suggestion_cn = "观望"

    # 构建结果
    module_summary = {}
    for wt in ["price", "updown", "trend", "resonance", "finance", "event", "risk"]:
        w = stock_warnings.get(wt)
        module_summary[wt] = {
            "color": w.indicator_color if w else "gray",
            "triggered": w.triggered if w else False,
        }

    return {
        "code": code,
        "name": name,
        "combined_color": combined_color,
        "combined_score": 0,  # 不再使用加权评分
        "suggestion": suggestion_cn,
        "suggestion_cn": suggestion_cn,
        "module_summary": module_summary,
    }


def check_decision_matrix(
    code: str,
    name: str,
    stock_warnings: Dict[str, WarningResult],
    thresholds: Dict[str, Any] = None,
) -> WarningResult:
    """综合决策矩阵入口函数"""
    decision = compute_decision(code, name, stock_warnings, thresholds)
    color = decision["combined_color"]

    level_map = {"gray": "info", "green": "info", "yellow": "warning",
                 "orange": "danger", "red": "danger", "blue": "warning", "black": "critical"}
    level = level_map.get(color, "info")

    title = f"{name}({code}) 综合决策: {decision['suggestion_cn']}"

    return WarningResult(
        code=code, warning_type="decision",
        warning_level=level, title=title,
        detail=str(decision),
        indicator_color=color,
        triggered=(color not in ("gray", "green", "yellow")),
    )
