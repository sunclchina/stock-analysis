"""
M05 智能分析引擎包。

遵循架构方案：
- DeepSeek大模型驱动
- 盘后复盘/个股分析/批量分析三种模式
- 提示词模板分离管理
- 自动重试3次，失败返回结构化"分析失败"消息

原则②：API Key/URL从.env读取
"""

from backend.services.analysis_engine.llm_client import LLMClient
from backend.services.analysis_engine.review import generate_review
from backend.services.analysis_engine.stock_analysis import analyze_stock
from backend.services.analysis_engine.batch_analysis import batch_analyze

__all__ = [
    "LLMClient",
    "generate_review",
    "analyze_stock",
    "batch_analyze",
]
