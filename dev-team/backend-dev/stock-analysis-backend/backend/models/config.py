"""
系统配置相关模型。
遵循架构方案 M06 配置模块定义。
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func, Boolean
from backend.config.database import Base


class WatchlistItem(Base):
    """自选股"""
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True, comment="用户ID")
    code = Column(String(10), nullable=False, comment="股票代码")
    name = Column(String(32), default="", comment="股票名称")
    added_reason = Column(String(256), default="", comment="加入原因")
    sort_order = Column(Integer, default=0, comment="排序序号")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<WatchlistItem(code={self.code}, user={self.user_id})>"


class MonitorItem(Base):
    """监控池标的"""
    __tablename__ = "monitor_pool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1, index=True, comment="用户ID")
    code = Column(String(10), nullable=False, comment="股票代码")
    name = Column(String(32), default="", comment="股票名称")
    monitor_type = Column(String(16), default="all", comment="监控类型：price/volume/all")
    threshold_high = Column(Float, nullable=True, comment="上限阈值")
    threshold_low = Column(Float, nullable=True, comment="下限阈值")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MonitorItem(code={self.code}, user={self.user_id})>"


class UserPreference(Base):
    """用户偏好设置"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), nullable=False, unique=True, comment="偏好键名")
    value = Column(Text, default="", comment="偏好值（JSON字符串）")
    description = Column(String(256), default="", comment="说明")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Preference(key={self.key})>"


class CustomDataSource(Base):
    """用户自定义数据源（付费第三方）"""
    __tablename__ = "custom_datasource"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, comment="数据源名称")
    api_url = Column(String(512), nullable=False, comment="API地址")
    api_key = Column(String(512), default="", comment="API密钥（Base64编码存储）")
    description = Column(String(256), default="", comment="描述")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<CustomDataSource(id={self.id}, name={self.name})>"
