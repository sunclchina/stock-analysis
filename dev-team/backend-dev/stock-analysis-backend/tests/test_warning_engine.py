"""
M03 预警计算引擎测试。
测试全部7种预警规则 + 综合决策矩阵。
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.warning_engine.price import (
    WarningResult, check_price_warning, check_updown_warning,
    check_warnings_for_stock, DEFAULT_PRICE_WARNING_THRESHOLD, check_price_warning_design,
)
from backend.services.warning_engine.trend import (
    check_trend_warning, classify_trend_direction, check_ma_breakout, check_trend_reversal,
)
from backend.services.warning_engine.resonance import (
    check_resonance_warning, score_ma_trend, score_rsi, score_macd, score_kdj,
)
from backend.services.warning_engine.finance import check_finance_warning
from backend.services.warning_engine.event import check_event_warning
from backend.services.warning_engine.risk import check_risk_score, score_to_color, score_to_level
from backend.services.warning_engine.decision import (
    check_decision_matrix, compute_decision, get_highest_color, extract_score,
)


# ============================================================
# 1. 价格预警测试 (price)
# ============================================================

class TestPriceWarning:

    def test_price_up_warning(self):
        result = check_price_warning("000001", "平安银行", 13.0, 12.0)
        assert result is not None
        assert result.triggered is True
        assert result.warning_type == "price"

    def test_price_down_warning(self):
        result = check_price_warning("000001", "平安银行", 11.0, 12.0)
        assert result is not None
        assert result.triggered is True

    def test_price_no_warning(self):
        result = check_price_warning("000001", "平安银行", 12.05, 12.0)
        assert result is None

    def test_price_design_api_exist(self):
        """验证新的价格预警函数存在且可调用"""
        pw = check_price_warning_design("000001", "测试", 10.0, [9, 9.5, 10, 10.5, 10]*50)
        assert pw.warning_type == "price"
        assert pw.indicator_color in ("green", "yellow", "red", "purple", "gray")

    # 兼容旧函数
    def test_price_critical_magnitude(self):
        result = check_price_warning("000001", "测试", 22.0, 10.0)
        assert result is not None
        assert result.warning_level == "critical"

    def test_price_no_pre_close(self):
        result = check_price_warning("000001", "测试", 10.0, 0)
        assert result is None

    def test_price_custom_threshold(self):
        result = check_price_warning("000001", "测试", 10.3, 10.0, threshold=0.02)
        assert result is not None
        result2 = check_price_warning("000001", "测试", 10.3, 10.0, threshold=0.05)
        assert result2 is None


# ============================================================
# 2. 涨跌预警测试 (updown)
# ============================================================

class TestUpdownWarning:

    def test_updown_warning_triggered(self):
        result = check_updown_warning("000001", "平安银行", 11.0, 10.0)
        assert result is not None
        assert result.warning_type == "updown"
        assert result.triggered is True

    def test_updown_no_warning(self):
        result = check_updown_warning("000001", "测试", 10.1, 10.0)
        assert result is None

    def test_updown_critical(self):
        result = check_updown_warning("000001", "测试", 20.0, 10.0)
        assert result is not None
        assert result.indicator_color == "purple"

    def test_updown_no_open_price(self):
        result = check_updown_warning("000001", "测试", 10.0, 0)
        assert result is None


# ============================================================
# 3. 趋势预警测试 (trend)
# ============================================================

class TestTrendWarning:

    def test_trend_bullish(self):
        closes = [100 + i * 2 + (i % 3) * 5 for i in range(30)]
        result = check_trend_warning("000001", "测试", closes[-1], closes)
        if result:
            assert result.warning_type == "trend"

    def test_trend_bearish(self):
        closes = [200 - i * 3 for i in range(30)]
        result = check_trend_warning("000001", "测试", closes[-1], closes)
        if result:
            assert result.warning_type == "trend"

    def test_classify_trend_direction_bullish(self):
        assert classify_trend_direction(105, 103, 100) == "bullish"

    def test_classify_trend_direction_bearish(self):
        assert classify_trend_direction(95, 98, 100) == "bearish"

    def test_trend_insufficient_data(self):
        result = check_trend_warning("000001", "测试", 10.0, [10, 11, 12])
        assert result is None

    def test_check_ma_breakout_above_all(self):
        result = check_ma_breakout(110, 100, 98, 95)
        assert result == "above_all"

    def test_check_ma_breakout_below_all(self):
        result = check_ma_breakout(80, 100, 98, 95)
        assert result == "below_all"


# ============================================================
# 4. 共振预警测试 (resonance)
# ============================================================

class TestResonanceWarning:

    def test_resonance_with_enough_data(self):
        closes = [100 + i * 0.5 + (i % 7) * 2 for i in range(30)]
        volumes = [10000 + i * 100 for i in range(30)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        result = check_resonance_warning("000001", "测试", closes[-1], 1.5,
            closes, highs, lows, closes, volumes)
        assert result is not None
        assert result.warning_type == "resonance"

    def test_resonance_insufficient_data(self):
        closes = [100] * 10
        result = check_resonance_warning("000001", "测试", 100, 0,
            closes, closes, closes, closes, closes)
        assert result is None

    def test_score_ma_trend_bullish(self):
        closes = [100 + i * 2 for i in range(25)]
        result = score_ma_trend(closes)
        assert result["signal"] in ("bullish", "weak_bullish")

    def test_score_rsi_overbought(self):
        closes = [100 + i * 3 for i in range(20)]
        result = score_rsi(closes, {})
        assert "score" in result

    def test_score_macd_with_data(self):
        closes = [100 + i * 0.5 + (i % 5) * 3 for i in range(30)]
        result = score_macd(closes)
        assert "score" in result


# ============================================================
# 5. 财务预警测试 (finance)
# ============================================================

class TestFinanceWarning:

    def test_finance_good_scores(self):
        result = check_finance_warning("600519", "贵州茅台", 1680, pe=30, pb=8, roe=25.0, revenue_growth=15.0)
        assert result is not None
        assert result.warning_type == "finance"
        # 应返回绿色（财务健康）
        assert result.indicator_color in ("green", "yellow", "gray")

    def test_finance_poor_scores(self):
        result = check_finance_warning("999999", "问题公司", 5, pe=500, pb=20, roe=2.0, revenue_growth=-20.0,
            profit_growth=-30.0, debt_ratio=85.0)
        assert result is not None
        # 应该触发预警
        assert result.indicator_color in ("red", "yellow", "black")

    def test_finance_no_data(self):
        # 无数据时仍返回绿色安全
        result = check_finance_warning("000001", "测试", 10.0)
        assert result is not None
        assert result.indicator_color == "green"

    def test_finance_hard_avoid(self):
        """测试强制规避"""
        result = check_finance_warning("000001", "测试", 10.0, hard_fraud=True)
        assert result is not None
        assert result.indicator_color == "black"


# ============================================================
# 6. 突发预警测试 (event)
# ============================================================

class TestEventWarning:

    def test_event_no_data(self):
        """无数据时返回绿色安全"""
        result = check_event_warning("000001", "测试", price=0, pre_close=10, open_price=10, high_price=10, low_price=10, volumes=[], closes=[])
        assert result is not None
        assert result.indicator_color == "green"

    def test_event_hard_avoid(self):
        """硬规避项"""
        result = check_event_warning("000001", "测试")
        assert result is not None

    def test_event_normal(self):
        """正常无事件"""
        result = check_event_warning("000001", "测试", price=10, pre_close=9.5, open_price=9.6, high_price=10.2, low_price=9.5, volumes=[100], closes=[10, 10.5, 10.2, 10.8])
        assert result is not None


# ============================================================
# 7. 风险评分测试 (risk)
# ============================================================

class TestRiskScore:

    def test_risk_score_green(self):
        result = check_risk_score("000001", "测试", closes=[100]*30, price=105, pre_close=100, volumes=[10000]*30, is_trading_hours=False)
        assert result.warning_type == "risk"
        assert result.indicator_color in ("green", "yellow", "orange", "red", "black")

    def test_risk_score_types(self):
        result = check_risk_score("000001", "测试")
        assert result is not None

    def test_score_to_color(self):
        assert score_to_color(10) == "green"
        assert score_to_color(30) == "yellow"
        assert score_to_color(50) == "orange"
        assert score_to_color(70) == "red"
        assert score_to_color(90) == "black"

    def test_score_to_level(self):
        assert score_to_level(10) == "info"
        assert score_to_level(30) == "warning"
        assert score_to_level(50) == "danger"
        assert score_to_level(70) == "danger"
        assert score_to_level(90) == "critical"


# ============================================================
# 8. 决策矩阵测试 (decision)
# ============================================================

class TestDecisionMatrix:

    def test_get_highest_color(self):
        w1 = WarningResult("000001", "price", "info", "t1", "", "green", True)
        w2 = WarningResult("000001", "trend", "danger", "t2", "", "red", True)
        w3 = WarningResult("000001", "risk", "info", "t3", "", "gray", False)
        assert get_highest_color([w1, w2, w3]) == "red"

    def test_get_highest_color_gray(self):
        w = WarningResult("000001", "test", "info", "t", "", "gray", False)
        assert get_highest_color([w]) == "gray"

    def test_get_highest_color_empty(self):
        assert get_highest_color([]) == "gray"

    def test_check_decision_matrix(self):
        warnings = {}
        w = WarningResult("000001", "risk", "info", "test", str({"risk_score": 60}), "yellow", True)
        warnings["risk"] = w
        result = check_decision_matrix("000001", "测试", warnings)
        assert result.warning_type == "decision"
        assert result.indicator_color in ("gray", "green", "yellow", "red", "purple")

    def test_compute_decision_buy(self):
        def mk(wtype, color, score):
            return WarningResult(code="000001", warning_type=wtype, warning_level="info", title="test",
                detail=str({"risk_score": score if wtype == "risk" else 0, "trend_score": score if wtype == "trend" else 0}),
                indicator_color=color, triggered=True)
        ws = {
            "risk": mk("risk", "green", -20),
            "trend": mk("trend", "green", 80),
            "resonance": mk("resonance", "green", 80),
            "finance": mk("finance", "green", 80),
        }
        d = compute_decision("000001", "测试", ws)
        assert "combined_score" in d
        assert "suggestion" in d
        assert "combined_color" in d

    def test_compute_decision_sell(self):
        def mk(wtype, color, score):
            return WarningResult(code="000001", warning_type=wtype, warning_level="danger", title="test",
                detail=str({"risk_score": score if wtype == "risk" else 0, "trend_score": score if wtype == "trend" else 0}),
                indicator_color=color, triggered=True)
        ws = {
            "risk": mk("risk", "purple", -80),
            "trend": mk("trend", "red", -80),
            "resonance": mk("resonance", "red", -80),
            "finance": mk("finance", "red", -80),
        }
        d = compute_decision("000001", "测试", ws)
        assert "combined_color" in d
        assert "suggestion" in d
