"""
预警模型。
包含预警记录和预警配置两种模型。

M03 智能预警模块，遵循架构方案：
- WarningRecord: 预警触发记录
- WarningConfig: 预警规则配置
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, func, Text, Boolean, JSON
from backend.config.database import Base


class WarningRecord(Base):
    """预警记录"""
    __tablename__ = "warning_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True, comment="股票代码")
    warning_type = Column(String(32), nullable=False, comment="预警类型：price/updown/trend/resonance/finance/event/risk")
    warning_level = Column(String(8), default="info", comment="预警级别：info/warning/danger/critical")
    title = Column(String(128), default="", comment="预警标题")
    detail = Column(Text, default="", comment="预警详情（JSON文本）")
    indicator_color = Column(String(8), default="gray", comment="指示颜色：gray/green/yellow/red/purple")
    is_acknowledged = Column(Boolean, default=False, comment="是否已处理")
    triggered_at = Column(DateTime, server_default=func.now(), comment="触发时间")
    acknowledged_at = Column(DateTime, nullable=True, comment="处理时间")

    def __repr__(self):
        return f"<Warning(id={self.id}, code={self.code}, type={self.warning_type}, level={self.warning_level})>"

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "warning_type": self.warning_type,
            "warning_level": self.warning_level,
            "title": self.title,
            "detail": self.detail,
            "indicator_color": self.indicator_color,
            "is_acknowledged": self.is_acknowledged,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


class WarningConfig(Base):
    """预警规则配置"""
    __tablename__ = "warning_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_type = Column(String(32), nullable=False, comment="配置类型：price/updown/trend/resonance/finance/event/risk")
    code = Column(String(10), nullable=True, comment="股票代码（全局配置时为null）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    params = Column(JSON, default=dict, comment="配置参数（JSON）")
    description = Column(String(256), default="", comment="配置说明")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<WarningConfig(id={self.id}, type={self.config_type}, code={self.code})>"

    def to_dict(self):
        return {
            "id": self.id,
            "config_type": self.config_type,
            "code": self.code,
            "is_active": self.is_active,
            "params": self.params,
            "description": self.description,
        }
