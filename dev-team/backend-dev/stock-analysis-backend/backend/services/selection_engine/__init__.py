"""
M04 智能选股引擎包（v3.0）。

设计文档 §5 架构要点：
- 五层过滤流水线：L1→财务+事件(前置)→L2→L3→综合评分
- 分批处理（每批200只，批次间 sleep 0.1s）
- 异步任务队列 + 结果缓存30分钟
- 财务数据预加载（FinancialDataLoader）
- 综合评分满分100: 45+20+25+10
"""

from backend.services.selection_engine.fixed import fixed_selection
from backend.services.selection_engine.custom import custom_selection
from backend.services.selection_engine.scorer import StockScorer, score_stock, sort_by_score
from backend.services.selection_engine.task_queue import SelectionTaskQueue, selection_task_queue, TaskStatus
from backend.services.selection_engine.financial_cache import FinancialDataLoader, financial_data_loader
from backend.services.selection_engine.batch_processor import BatchProcessor, batch_filter, batch_map

__all__ = [
    "fixed_selection",
    "custom_selection",
    "StockScorer",
    "score_stock",
    "sort_by_score",
    "SelectionTaskQueue",
    "selection_task_queue",
    "TaskStatus",
    "FinancialDataLoader",
    "financial_data_loader",
    "BatchProcessor",
    "batch_filter",
    "batch_map",
]
