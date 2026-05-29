"""
操盘笔记模型。
长期保存用户的操盘记录、观察思考。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func, Boolean
from backend.config.database import Base


class TradingNote(Base):
    """操盘笔记"""
    __tablename__ = "trading_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True, comment="用户ID")
    title = Column(String(128), nullable=False, default="", comment="笔记标题")
    content = Column(Text, default="", comment="笔记正文")
    stock_code = Column(String(10), default="", comment="关联股票代码（可选）")
    stock_name = Column(String(32), default="", comment="关联股票名称（可选）")
    tags = Column(String(256), default="", comment="标签，逗号分隔")
    is_pinned = Column(Boolean, default=False, comment="是否置顶")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<TradingNote(id={self.id}, title={self.title})>"
