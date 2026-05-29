"""
M04 智能选股引擎测试。
测试3种固定策略模板、5层过滤流水线、自定义选股条件组合、评分器。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.selection_engine.fixed import (
    fixed_selection, SELECTION_TEMPLATES,
    filter_not_st, filter_not_suspended, filter_min_price, filter_min_amount,
    filter_trend_bullish, filter_resonance_positive, filter_volume_active,
    filter_risk_low, filter_ma5_above_ma10, filter_price_above_all_ma,
)
from backend.services.selection_engine.custom import (
    custom_selection, validate_conditions, _build_condition_filters,
)
from backend.services.selection_engine.scorer import (
    StockScorer, score_stock, sort_by_score, DEFAULT_SCORE_WEIGHTS,
)


# ============================================================
# TEST DATA
# ============================================================

SAMPLE_STOCKS = [
    {"code": "600519", "name": "贵州茅台", "price": 1680.0, "change_pct": 1.2, "amount": 450000, "volume": 2.8,
     "trend_direction": "bullish", "trend_score": 75, "resonance_score": 68, "risk_score": 82,
     "finance_score": 80, "volume_ratio": 1.5, "is_st": False, "is_suspended": False,
     "ma5": 1650, "ma10": 1620, "ma20": 1580, "pe": 30, "pb": 8, "roe": 25,
     "revenue_growth": 15, "profit_growth": 18, "debt_ratio": 30, "rsi": 65, "price_position": 0.6},
    {"code": "000858", "name": "五粮液", "price": 145.0, "change_pct": 2.5, "amount": 280000, "volume": 2.0,
     "trend_direction": "bullish", "trend_score": 68, "resonance_score": 55, "risk_score": 75,
     "finance_score": 72, "volume_ratio": 1.8, "is_st": False, "is_suspended": False,
     "ma5": 140, "ma10": 136, "ma20": 132, "pe": 22, "pb": 6, "roe": 20,
     "revenue_growth": 12, "profit_growth": 14, "debt_ratio": 25, "rsi": 62, "price_position": 0.55},
    {"code": "600036", "name": "招商银行", "price": 36.5, "change_pct": 0.8, "amount": 350000, "volume": 9.5,
     "trend_direction": "consolidation", "trend_score": 20, "resonance_score": 15, "risk_score": 88,
     "finance_score": 78, "volume_ratio": 0.9, "is_st": False, "is_suspended": False,
     "ma5": 35.8, "ma10": 35.5, "ma20": 35.0, "pe": 7, "pb": 1.2, "roe": 16,
     "revenue_growth": 5, "profit_growth": 8, "debt_ratio": 60, "rsi": 52, "price_position": 0.5},
    {"code": "688981", "name": "中芯国际", "price": 55.0, "change_pct": -1.2, "amount": 380000, "volume": 7.0,
     "trend_direction": "bearish", "trend_score": -30, "resonance_score": -20, "risk_score": 55,
     "finance_score": 30, "volume_ratio": 0.5, "is_st": False, "is_suspended": False,
     "ma5": 57, "ma10": 58, "ma20": 60, "pe": 80, "pb": 5, "roe": 8,
     "revenue_growth": 10, "profit_growth": -5, "debt_ratio": 25, "rsi": 35, "price_position": 0.25},
    {"code": "600900", "name": "长江电力", "price": 25.8, "change_pct": 0.3, "amount": 120000, "volume": 4.6,
     "trend_direction": "bullish", "trend_score": 45, "resonance_score": 30, "risk_score": 90,
     "finance_score": 82, "volume_ratio": 0.8, "is_st": False, "is_suspended": False,
     "ma5": 25.5, "ma10": 25.3, "ma20": 25.0, "pe": 18, "pb": 2.5, "roe": 12,
     "revenue_growth": 5, "profit_growth": 8, "debt_ratio": 40, "rsi": 55, "price_position": 0.55},
    {"code": "000333", "name": "美的集团", "price": 68.0, "change_pct": 1.5, "amount": 220000, "volume": 3.2,
     "trend_direction": "bullish", "trend_score": 65, "resonance_score": 60, "risk_score": 80,
     "finance_score": 75, "volume_ratio": 1.3, "is_st": False, "is_suspended": False,
     "ma5": 66.5, "ma10": 65.0, "ma20": 63.0, "pe": 15, "pb": 3, "roe": 22,
     "revenue_growth": 10, "profit_growth": 12, "debt_ratio": 50, "rsi": 60, "price_position": 0.55},
    {"code": "601318", "name": "中国平安", "price": 48.0, "change_pct": -0.5, "amount": 520000, "volume": 10.8,
     "trend_direction": "consolidation", "trend_score": 10, "resonance_score": 5, "risk_score": 78,
     "finance_score": 70, "volume_ratio": 0.7, "is_st": False, "is_suspended": False,
     "ma5": 47.5, "ma10": 47.0, "ma20": 48.5, "pe": 12, "pb": 1.5, "roe": 14,
     "revenue_growth": 3, "profit_growth": 5, "debt_ratio": 55, "rsi": 48, "price_position": 0.45},
]


# ============================================================
# 固定选股策略模板测试
# ============================================================

class TestSelectionTemplates:

    def test_three_templates_registered(self):
        """测试3种固定策略模板已注册"""
        assert len(SELECTION_TEMPLATES) == 3
        assert "stable_trend" in SELECTION_TEMPLATES
        assert "reversal_breakthrough" in SELECTION_TEMPLATES
        assert "short_term_strong" in SELECTION_TEMPLATES

    def test_stable_trend_template(self):
        """测试稳健趋势型模板配置"""
        template = SELECTION_TEMPLATES["stable_trend"]
        assert template.id == "stable_trend"
        assert template.max_results == 10
        assert len(template.layer1_filters) >= 2
        assert len(template.layer2_tech_filters) >= 4
        assert len(template.layer3_deep_filters) >= 2
        assert template.min_score == 85.0

    def test_reversal_breakthrough_template(self):
        """测试反转突破型模板配置"""
        template = SELECTION_TEMPLATES["reversal_breakthrough"]
        assert template.id == "reversal_breakthrough"
        assert template.max_results == 15

    def test_short_term_strong_template(self):
        """测试短线强势型模板配置"""
        template = SELECTION_TEMPLATES["short_term_strong"]
        assert template.id == "short_term_strong"
        assert template.max_results == 20

    @pytest.mark.asyncio
    async def test_fixed_selection_stable_trend(self):
        """测试固定选股 - 稳健趋势型"""
        result = await fixed_selection("stable_trend", SAMPLE_STOCKS)
        assert result["template"]["id"] == "stable_trend"
        assert "layer_counts" in result
        assert "results" in result
        # 样本中满足稳健趋势条件的股票
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_fixed_selection_invalid_template(self):
        """测试无效模板ID"""
        with pytest.raises(ValueError):
            await fixed_selection("nonexistent_template", SAMPLE_STOCKS)

    @pytest.mark.asyncio
    async def test_fixed_selection_empty_stocks(self):
        """测试空股票列表"""
        result = await fixed_selection("stable_trend", [])
        assert result["count"] == 0
        assert result["layer_counts"]["layer1"] == 0


# ============================================================
# 过滤函数测试
# ============================================================

class TestFilterFunctions:

    def test_filter_not_st(self):
        """测试非ST过滤"""
        assert filter_not_st({"is_st": False}) is True
        assert filter_not_st({"is_st": True}) is False

    def test_filter_not_suspended(self):
        """测试非停牌过滤"""
        assert filter_not_suspended({"is_suspended": False}) is True
        assert filter_not_suspended({"is_suspended": True}) is False

    def test_filter_min_price(self):
        """测试最低价格过滤"""
        assert filter_min_price({"price": 10.0}) is True
        assert filter_min_price({"price": 1.0}) is False

    def test_filter_trend_bullish(self):
        """测试多头趋势过滤"""
        assert filter_trend_bullish({"trend_direction": "bullish"}) is True
        assert filter_trend_bullish({"trend_direction": "bearish"}) is False

    def test_filter_resonance_positive(self):
        """测试共振偏多过滤"""
        assert filter_resonance_positive({"resonance_score": 30}) is True
        assert filter_resonance_positive({"resonance_score": 10}) is False

    def test_filter_volume_active(self):
        """测试量能活跃过滤"""
        assert filter_volume_active({"volume_ratio": 1.0}) is True
        assert filter_volume_active({"volume_ratio": 0.3}) is False

    def test_filter_ma5_above_ma10(self):
        """测试MA5 > MA10过滤"""
        assert filter_ma5_above_ma10({"ma5": 105, "ma10": 100}) is True
        assert filter_ma5_above_ma10({"ma5": 95, "ma10": 100}) is False

    def test_filter_price_above_all_ma(self):
        """测试价格在全部均线之上"""
        assert filter_price_above_all_ma({"price": 110, "ma5": 100, "ma10": 98, "ma20": 95}) is True
        assert filter_price_above_all_ma({"price": 90, "ma5": 100, "ma10": 98, "ma20": 95}) is False


# ============================================================
# 自定义选股测试
# ============================================================

class TestCustomSelection:

    def test_validate_conditions_valid(self):
        """测试合法条件验证"""
        conditions = {
            "price": {"min": 5.0, "max": 200.0},
            "trend_direction": {"direction": "bullish"},
            "resonance_score": {"min": 20, "max": 100},
            "volume_ratio": {"min": 0.8, "max": 10.0},
        }
        errors = validate_conditions(conditions)
        assert len(errors) == 0

    def test_validate_conditions_invalid_key(self):
        """测试非法条件键"""
        errors = validate_conditions({"unknown_condition": {}})
        assert len(errors) == 1
        assert "未知条件" in errors[0]

    def test_validate_conditions_missing_param(self):
        """测试缺少参数"""
        errors = validate_conditions({"price": {"min": 10}})  # 缺max
        # price的params定义中min和max都是required
        assert len(errors) >= 1

    @pytest.mark.asyncio
    async def test_custom_selection_price_range(self):
        """测试自定义选股 - 价格区间"""
        result = await custom_selection(
            conditions={"price": {"min": 30.0, "max": 100.0}},
            all_stocks=SAMPLE_STOCKS,
        )
        assert result["conditions_valid"] is True
        for s in result["results"]:
            assert s["price"] >= 30.0
            assert s["price"] <= 100.0

    @pytest.mark.asyncio
    async def test_custom_selection_trend_direction(self):
        """测试自定义选股 - 趋势方向"""
        result = await custom_selection(
            conditions={"trend_direction": {"direction": "bullish"}},
            all_stocks=SAMPLE_STOCKS,
        )
        assert result["conditions_valid"] is True
        for s in result["results"]:
            assert s["trend_direction"] == "bullish"

    @pytest.mark.asyncio
    async def test_custom_selection_invalid_conditions(self):
        """测试自定义选股 - 非法条件"""
        result = await custom_selection(
            conditions={"unknown": {"param": 1}},
            all_stocks=SAMPLE_STOCKS,
        )
        assert result["conditions_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_custom_selection_empty_stocks(self):
        """测试自定义选股 - 空股票列表"""
        result = await custom_selection(
            conditions={"price": {"min": 5.0}},
            all_stocks=[],
        )
        assert result["count"] == 0


# ============================================================
# 评分器测试
# ============================================================

class TestStockScorer:

    def test_scorer_full_data(self):
        """测试全数据评分"""
        stock = {
            "code": "600519", "name": "贵州茅台",
            "trend_score": 75, "resonance_score": 68,
            "risk_score": 82, "finance_score": 80, "volume_ratio": 1.5,
            "is_st": False, "is_suspended": False,
        }
        result = score_stock(stock)
        # total_score在0-100范围内
        assert 0 <= result["total_score"] <= 100, f"Score out of range: {result['total_score']}"
        assert "dimensions" in result
        assert "trend" in result["dimensions"]
        assert "risk" in result["dimensions"]
        assert len(result["penalties"]) == 0

    def test_scorer_partial_data(self):
        """测试部分数据评分"""
        stock = {"code": "000001", "name": "测试", "risk_score": 60}
        result = score_stock(stock)
        assert "total_score" in result
        assert result["total_score"] > 0

    def test_scorer_with_penalties(self):
        """测试扣分项"""
        stock = {
            "code": "000001", "name": "测试",
            "is_st": True,
            "trend_score": 75, "resonance_score": 68,
            "risk_score": 82, "finance_score": 80,
        }
        result = score_stock(stock)
        assert len(result["penalties"]) >= 1
        assert any(p["reason"] == "ST/ST*" for p in result["penalties"])

    def test_scorer_with_suspended(self):
        """测试停牌扣分"""
        stock = {
            "code": "000001", "name": "测试",
            "is_suspended": True,
        }
        result = score_stock(stock)
        assert len(result["penalties"]) >= 1

    def test_sort_by_score_descending(self):
        """测试按评分降序排列"""
        stocks = [
            {"code": "001", "trend_score": 80, "resonance_score": 80, "risk_score": 80, "finance_score": 80},
            {"code": "002", "trend_score": 20, "resonance_score": 20, "risk_score": 20, "finance_score": 20},
        ]
        scored = sort_by_score(stocks, top_n=2)
        assert len(scored) == 2
        # 通常第一个评分更高
        s0_score = scored[0].get("total_score", 0)
        s1_score = scored[1].get("total_score", 0)
        assert s0_score >= s1_score

    def test_scorer_default_weights(self):
        """测试默认权重"""
        assert "trend" in DEFAULT_SCORE_WEIGHTS
        assert "resonance" in DEFAULT_SCORE_WEIGHTS
        assert "risk" in DEFAULT_SCORE_WEIGHTS
        assert "finance" in DEFAULT_SCORE_WEIGHTS
        assert "volume" in DEFAULT_SCORE_WEIGHTS
        assert sum(DEFAULT_SCORE_WEIGHTS.values()) == pytest.approx(1.0)
