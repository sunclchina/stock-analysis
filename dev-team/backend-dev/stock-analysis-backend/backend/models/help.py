"""
帮助中心 — 数据模型。

包含5张表：
- HelpCategory: 分类
- HelpDocument: 文档
- HelpDocumentHistory: 文档版本历史
- HelpFeedback: 文档反馈
- HelpContact: 联系我们
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
)
from backend.config.database import Base


class HelpCategory(Base):
    """帮助分类表"""
    __tablename__ = "help_category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="分类名称")
    icon = Column(String(50), default="", comment="图标emoji")
    sort_order = Column(Integer, default=0, comment="排序权重")
    status = Column(Integer, default=1, comment="1启用 0禁用")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class HelpDocument(Base):
    """帮助文档表"""
    __tablename__ = "help_document"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("help_category.id"), nullable=False, index=True, comment="分类ID")
    title = Column(String(200), nullable=False, comment="标题")
    slug = Column(String(200), unique=True, index=True, comment="URL友好标识")
    content = Column(Text, default="", comment="Markdown内容")
    summary = Column(String(500), default="", comment="摘要")
    tags = Column(String(500), default="", comment="标签（逗号分隔）")
    read_time = Column(Integer, default=0, comment="阅读时长（分钟）")
    author = Column(String(50), default="系统", comment="作者")
    view_count = Column(Integer, default=0, comment="浏览量")
    like_count = Column(Integer, default=0, comment="有用数")
    dislike_count = Column(Integer, default=0, comment="无用数")
    sort_order = Column(Integer, default=0, comment="排序权重")
    status = Column(Integer, default=0, comment="1发布 0草稿 2下架")
    version = Column(Integer, default=1, comment="当前版本号")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime, nullable=True, comment="发布时间")


class HelpDocumentHistory(Base):
    """文档版本历史表"""
    __tablename__ = "help_document_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("help_document.id"), nullable=False, index=True, comment="文档ID")
    version = Column(Integer, nullable=False, comment="版本号")
    content = Column(Text, default="", comment="该版本内容")
    change_log = Column(String(500), default="", comment="变更说明")
    operator = Column(String(50), default="", comment="操作人")
    created_at = Column(DateTime, default=datetime.now)


class HelpFeedback(Base):
    """文档反馈表"""
    __tablename__ = "help_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("help_document.id"), nullable=True, index=True, comment="文档ID（可选）")
    feedback_type = Column(Integer, nullable=False, comment="1有用 2无用")
    reason = Column(String(500), default="", comment="反馈原因")
    user_id = Column(Integer, nullable=True, default=0, comment="用户ID")
    contact = Column(String(100), default="", comment="联系方式")
    user_agent = Column(String(500), default="", comment="浏览器信息")
    created_at = Column(DateTime, default=datetime.now)


class HelpContact(Base):
    """联系反馈表"""
    __tablename__ = "help_contact"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Integer, nullable=False, comment="1使用问题 2Bug 3建议 4文档 5其他")
    title = Column(String(200), default="", comment="标题")
    content = Column(Text, default="", comment="详细描述")
    attachment = Column(String(500), default="", comment="附件路径")
    contact = Column(String(100), default="", comment="联系方式")
    user_id = Column(Integer, nullable=True, default=0, comment="用户ID")
    status = Column(Integer, default=0, comment="0待处理 1处理中 2已解决 3已关闭")
    reply = Column(Text, default="", comment="回复内容")
    replied_by = Column(String(50), default="", comment="回复人")
    replied_at = Column(DateTime, nullable=True, comment="回复时间")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
