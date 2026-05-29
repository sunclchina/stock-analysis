"""
分析报告模型。
预留供 M05 分析模块使用。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON
from backend.config.database import Base


class AnalysisReport(Base):
    """分析报告"""
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True, comment="用户ID")
    report_type = Column(String(16), nullable=False, comment="报告类型：review/stock/batch")
    title = Column(String(128), default="", comment="报告标题")
    input_params = Column(JSON, nullable=True, comment="输入参数")
    content = Column(Text, default="", comment="报告内容（Markdown）")
    summary = Column(String(512), default="", comment="摘要")
    status = Column(String(16), default="pending", comment="状态：pending/running/completed/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    def __repr__(self):
        return f"<Report(id={self.id}, type={self.report_type}, status={self.status}, user={self.user_id})>"
