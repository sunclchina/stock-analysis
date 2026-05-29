"""
M04 选股引擎 — 综合评分器（v3.0 设计文档 §5.2.5）。

满分100分评分体系：
- 技术面趋势与共振 45分（趋势方向+25/20，共振+20，强度≥80额外+5）
- 价格位置与量价健康 20分（价位20%-55%+10，量价健康+10）
- 财务安全度 25分（🟢+15，净利润增速>10%+5，负债率<50%+5）
- 事件风险控制 10分（无负面事件+10）

输出分级：
- 90-100: 核心精选（核心精选）
- 85-89: 优质标的（优质标的）
- 70-84: 稳健关注（不进推荐）
- <70: 排除
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 输出分级阈值
GRADE_LEVELS = [
    (90, "核心精选", "重点关注，可建仓"),
    (85, "优质标的", "正常参与"),
    (70, "稳健关注", "轻仓关注"),
]


class StockScorer:
    """
    综合评分器（设计文档§5.2.5）。
    满分100分：45 + 20 + 25 + 10
    """

    def score(self, stock: Dict[str, Any], strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        综合评分，支持方案适配加分。
        
        Args:
            stock: 股票数据
            strategy: 方案ID（steady_trend / reversal_breakout / short_term_strong）
        """
        code = stock.get("code", "")
        name = stock.get("name", "")
        dimensions = {}

        # 维度1：技术面趋势与共振（45分）
        trend_score = self._score_trend_resonance(stock)

        # 短线强势型：趋势强度额外+5分
        if strategy == "short_term_strong":
            trend_score += 5

        # 反转突破型：反转趋势额外+5分
        if strategy == "reversal_breakout":
            direction = stock.get("trend_direction", "")
            if direction in ("reversal", "blue", "bullish_reversal") or stock.get("_is_reversal_by_formula", False):
                trend_score += 5

        # 反转放量≥1.5倍额外+3分（反转突破型特有）
        if strategy == "reversal_breakout":
            vol_ratio = stock.get("volume_ratio", 0)
            if vol_ratio and float(vol_ratio) >= 1.5:
                # 这个加分已在 price_volume 中实现，这里不加了避免重复
                pass

        trend_score = min(trend_score, 50)  # 含加分不超过50
        dimensions["trend_resonance"] = {"raw": trend_score, "max": 45}
        total = trend_score

        # 维度2：价格位置与量价健康（20分 + 方案加分）
        price_vol_score = self._score_price_volume(stock)

        # 反转突破型：放量1.5倍以上额外+3分
        if strategy == "reversal_breakout":
            vol_ratio = stock.get("volume_ratio", 0)
            if vol_ratio and float(vol_ratio) >= 1.5:
                price_vol_score += 3

        # 短线强势型：量比≥1.5额外+3分
        if strategy == "short_term_strong":
            vol_ratio = stock.get("volume_ratio", 0)
            if vol_ratio and float(vol_ratio) >= 1.5:
                price_vol_score += 3

        price_vol_score = min(price_vol_score, 23)  # 含加分不超过23
        dimensions["price_volume"] = {"raw": price_vol_score, "max": 20}
        total += price_vol_score

        # 维度3：财务安全度（25分 + 方案加分）
        finance_score = self._score_finance(stock)

        # 稳健趋势型：财务维度额外+5分
        if strategy == "steady_trend":
            finance_score += 5

        finance_score = min(finance_score, 30)  # 含加分不超过30
        dimensions["finance"] = {"raw": finance_score, "max": 25}
        total += finance_score

        # 维度4：事件风险控制（10分）
        event_score = self._score_event(stock)
        dimensions["event"] = {"raw": event_score, "max": 10}
        total += event_score

        total = max(0.0, min(100.0, total))

        # 输出分级
        grade_name, advice = self._get_grade_and_advice(total)

        return {
            "code": code,
            "name": name,
            "total_score": round(total, 2),
            "dimensions": dimensions,
            "grade": grade_name,
            "trade_advice": advice,
            "breakdown": self._build_breakdown(dimensions, total, grade_name),
        }

    def _score_trend_resonance(self, stock: Dict[str, Any]) -> float:
        """
        技术面趋势与共振评分（满分45分）。
        25分趋势方向 + 20分共振 + 5分强度加分
        """
        score = 0.0
        direction = stock.get("trend_direction", "")
        trend_strength = abs(stock.get("trend_score", 0) or 0)

        # 趋势方向得分（0-25分）
        if direction in ("bullish", "up"):
            score += 25
        elif direction in ("reversal", "blue", "bullish_reversal"):
            score += 20
        elif direction == "consolidation":
            score += 10
        else:
            score += 0

        # 共振评分（0-20分）
        res_pos = stock.get("resonance_positive_count", stock.get("resonance_positive", 0))
        try:
            res_pos = int(res_pos)
        except (ValueError, TypeError):
            res_pos = 0

        if res_pos >= 8:
            score += 20
        elif res_pos >= 7:
            score += 18
        elif res_pos >= 6:
            score += 15
        elif res_pos >= 5:
            score += 12
        elif res_pos >= 4:
            score += 8
        elif res_pos >= 3:
            score += 5
        elif res_pos >= 2:
            score += 3
        elif res_pos >= 1:
            score += 1

        # 趋势强度≥80额外+5分（已包含在45分基数内）
        if trend_strength >= 80:
            score += 5

        return min(score, 50)

    def _score_price_volume(self, stock: Dict[str, Any]) -> float:
        """
        价格位置与量价健康度评分（满分20分）。
        价位位置(10分) + 量价健康(10分)
        """
        score = 0.0

        # 价位位置（0-10分）：20%-55%满分
        pos = stock.get("price_position", 0.5) or 0.5
        try:
            pos = float(pos)
        except (ValueError, TypeError):
            pos = 0.5

        if 0.20 <= pos <= 0.55:
            score += 10
        elif 0.15 <= pos <= 0.65:
            score += 7
        elif 0.10 <= pos <= 0.75:
            score += 4
        elif pos <= 0.10:
            score += 2  # 超低位
        else:
            score += 1  # 高位

        # 量价健康（0-10分）
        vol_ratio = stock.get("volume_ratio", 1.0) or 1.0
        change = stock.get("change_pct", 0) or 0
        try:
            vol_ratio = float(vol_ratio)
            change = float(change)
        except (ValueError, TypeError):
            vol_ratio = 1.0
            change = 0

        if change > 2 and vol_ratio > 1.5:
            score += 10  # 强势放量上涨
        elif 0 < change <= 2 and vol_ratio > 1.2:
            score += 8
        elif change > 0 and vol_ratio > 0.8:
            score += 6
        elif change < 0 and vol_ratio < 0.8:
            score += 7  # 下跌缩量（健康回调）
        elif change < 0 and 0.8 <= vol_ratio <= 1.0:
            score += 4
        elif vol_ratio > 0.5:
            score += 2
        else:
            score += 0

        return min(score, 23)

    def _score_finance(self, stock: Dict[str, Any]) -> float:
        """
        财务安全度评分（满分25分）。
        等级🟢+15 + 净利润增速>10%+5 + 负债率<50%+5
        """
        score = 0.0

        # 财务安全等级（0-15分）
        finance_grade = stock.get("finance_grade", stock.get("finance_color", ""))
        if isinstance(finance_grade, str) and finance_grade.lower() in ("green", "a", "safe"):
            score += 15
        elif isinstance(finance_grade, str) and finance_grade.lower() in ("yellow", "b"):
            score += 8
        else:
            score += 2

        # 净利润增速 > 10%（0-5分）
        profit_growth = stock.get("profit_growth", stock.get("net_profit_growth")) or 0
        try:
            profit_growth = float(profit_growth)
        except (ValueError, TypeError):
            profit_growth = 0

        if profit_growth > 10:
            score += 5
        elif profit_growth > 0:
            score += 2

        # 负债率 < 50%（0-5分）
        debt_ratio = stock.get("debt_ratio")
        if debt_ratio is not None:
            try:
                debt_ratio = float(debt_ratio)
                if debt_ratio < 50:
                    score += 5
                elif debt_ratio < 60:
                    score += 3
                elif debt_ratio < 75:
                    score += 1
            except (ValueError, TypeError):
                pass

        return min(score, 30)

    def _score_event(self, stock: Dict[str, Any]) -> float:
        """
        事件风险控制评分（满分10分）。
        无负面事件+10分，每项负面事件减分。
        """
        # 起始10分，无负面事件
        penalty = 0

        # 检查各类负面事件
        if stock.get("debt_default_flag", False):
            penalty += 10
        if stock.get("csrc_investigation_flag", False):
            penalty += 10
        if stock.get("fraud_flag", False):
            penalty += 10
        if stock.get("public_censure_flag", False):
            penalty += 8
        if (stock.get("planned_reduction_pct", 0) or 0) > 5:
            penalty += 5
        if (stock.get("pledge_ratio", 0) or 0) > 80:
            penalty += 3

        lawsuit = stock.get("lawsuit_amount", 0) or 0
        net_asset = stock.get("net_asset", 1) or 1
        if lawsuit > net_asset * 0.2:
            penalty += 3

        # 无明确事件数据时，基于风险评分给分
        if not any([
            stock.get("debt_default_flag") is not None,
            stock.get("csrc_investigation_flag") is not None,
        ]):
            risk = stock.get("risk_score", 50) or 50
            try:
                risk = float(risk)
            except (ValueError, TypeError):
                risk = 50
            if risk <= 20:
                return 10
            elif risk <= 30:
                return 9
            elif risk <= 40:
                return 8
            elif risk <= 50:
                return 6
            else:
                return 4

        return max(0, 10 - penalty)

    @staticmethod
    def _get_grade_and_advice(total_score: float) -> Tuple[str, str]:
        """获取输出分级和操作建议"""
        for threshold, grade, advice in GRADE_LEVELS:
            if total_score >= threshold:
                return grade, advice
        return "排除", "不推荐"

    @staticmethod
    def _build_breakdown(
        dimensions: Dict[str, Dict], total: float, grade: str
    ) -> str:
        label_map = {
            "trend_resonance": "趋势共振",
            "price_volume": "价量健康",
            "finance": "财务安全",
            "event": "事件风险",
        }
        parts = []
        for dim_name, dim_data in dimensions.items():
            label = label_map.get(dim_name, dim_name)
            parts.append(f"{label}={dim_data['raw']:.0f}/{dim_data['max']}")
        parts.append(f"总分={total:.1f}")
        parts.append(f"评级={grade}")
        return " | ".join(parts)


def score_stock(
    stock: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
    strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """单只股票评分（weights 参数保留兼容，不再使用）"""
    return StockScorer().score(stock, strategy=strategy)


def sort_by_score(
    stocks: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    top_n: int = 20,
    strategy: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    批量评分排序。
    
    Args:
        stocks: 股票列表
        weights: (保留参数，不再使用)
        top_n: 返回前N只
        strategy: 方案ID，用于方案特异加分
        
    Returns:
        按总分降序排列的股票列表（含评分字段）
    """
    scorer = StockScorer()
    scored = []
    for stock in stocks:
        try:
            result = scorer.score(stock, strategy=strategy)
            merged = {
                **stock,
                "total_score": result["total_score"],
                "score_dimensions": result["dimensions"],
                "grade": result["grade"],
                "trade_advice": result["trade_advice"],
                "score_breakdown": result["breakdown"],
            }
            scored.append((result["total_score"], merged))
        except Exception as e:
            logger.warning(f"评分失败 [{stock.get('code', '?')}]: {e}")

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_n]]
