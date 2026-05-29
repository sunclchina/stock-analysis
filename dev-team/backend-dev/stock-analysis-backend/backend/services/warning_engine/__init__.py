"""
M03 预警计算引擎包。
遵循架构方案第六节 services/warning_engine/ 目录结构。

完整7大模块 + 综合决策矩阵：
1. price      - 价格预警
2. updown     - 涨跌预警（在price.py中实现）
3. trend      - 趋势预警
4. resonance  - 共振预警
5. finance    - 财务预警
6. event      - 突发预警
7. risk       - 风险评分
8. decision   - 综合决策矩阵
"""

from backend.services.warning_engine.engine import WarningEngine, check_all_warnings
from backend.services.warning_engine.price import (
    WarningResult,
    check_price_warning,
    check_updown_warning,
    check_warnings_for_stock,
)
from backend.services.warning_engine.trend import (
    check_trend_warning,
    classify_trend_direction,
    check_ma_breakout,
    check_trend_reversal,
)
from backend.services.warning_engine.resonance import check_resonance_warning
from backend.services.warning_engine.finance import check_finance_warning
from backend.services.warning_engine.event import check_event_warning
from backend.services.warning_engine.risk import check_risk_score, score_to_color, score_to_level
from backend.services.warning_engine.decision import check_decision_matrix, compute_decision

__all__ = [
    # 主引擎
    "WarningEngine",
    "check_all_warnings",
    # 预警结果
    "WarningResult",
    # 各模块检查函数
    "check_price_warning",
    "check_updown_warning",
    "check_warnings_for_stock",
    "check_trend_warning",
    "check_resonance_warning",
    "check_finance_warning",
    "check_event_warning",
    "check_risk_score",
    "check_decision_matrix",
    # 工具函数
    "classify_trend_direction",
    "check_ma_breakout",
    "check_trend_reversal",
    "score_to_color",
    "score_to_level",
    "compute_decision",
]
