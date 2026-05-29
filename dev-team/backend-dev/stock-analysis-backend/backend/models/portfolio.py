"""
资产组合管理 — 数据模型。

遵循设计文档 v1.5 §9 数据库核心表结构，适配 SQLAlchemy + SQLite。
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON, BigInteger, UniqueConstraint, Index
)
from backend.config.database import Base


class VirtualAccount(Base):
    """虚拟账户表"""
    __tablename__ = "virtual_account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(50), nullable=False, default="新账户")
    initial_capital = Column(Float, nullable=False, default=1000000.00)
    current_assets = Column(Float, nullable=False, default=0.0)
    available_cash = Column(Float, nullable=False, default=0.0)
    auto_trade_enabled = Column(Integer, default=0)  # 0=手动 1=自动
    strategy_id = Column(Integer, nullable=True)
    auto_trade_status = Column(Integer, default=0)  # 0=暂停 1=运行
    version = Column(Integer, default=0)  # 乐观锁
    status = Column(Integer, default=1)  # 1=正常 0=归档
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Position(Base):
    """持仓表"""
    __tablename__ = "position"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), default="")
    quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, default=0.0)
    profit_loss = Column(Float, default=0.0)
    profit_loss_rate = Column(Float, default=0.0)
    source_type = Column(Integer, default=0)  # 0=手动 1=自动
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("account_id", "stock_code", name="uk_account_stock"),
    )


class TransactionRecord(Base):
    """交易记录表"""
    __tablename__ = "transaction_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), default="")
    trade_type = Column(Integer, nullable=False)  # 1=买入 2=卖出
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    order_id = Column(String(50), default="")
    strategy_triggered = Column(Integer, default=0)  # 0=手动 1=策略触发
    order_status = Column(Integer, default=0)  # 0=已提交 1=部分成交 2=完全成交 3=已取消
    notes = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_account_id", "account_id"),
        Index("idx_created_at", "created_at"),
    )


class Strategy(Base):
    """策略配置表"""
    __tablename__ = "strategy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    strategy_type = Column(String(20), default="波段")  # 短线/波段/价值/反转
    period = Column(String(10), default="日")
    config_json = Column(JSON, nullable=False, default=dict)
    description = Column(String(500), default="")
    status = Column(Integer, default=1)  # 1=启用 0=禁用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class BacktestTask(Base):
    """回测任务表"""
    __tablename__ = "backtest_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    init_capital = Column(Float, nullable=False)
    result_json = Column(JSON, nullable=True)
    status = Column(Integer, default=0)  # 0=待执行 1=执行中 2=完成 3=失败
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


class ClosePositionRecord(Base):
    """清仓记录表"""
    __tablename__ = "close_position_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    stock_name = Column(String(50), default="")
    buy_time = Column(DateTime, nullable=True)
    sell_time = Column(DateTime, nullable=True)
    hold_days = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    total_profit_rate = Column(Float, default=0.0)
    trade_type = Column(Integer, default=2)  # 2=手动清仓 3=策略清仓
    reason = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.now)
