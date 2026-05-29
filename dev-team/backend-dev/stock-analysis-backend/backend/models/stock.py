"""
股票基本信息模型。
遵循架构方案第六节 backend/models/stock.py 定义。
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, func
from backend.config.database import Base


class StockInfo(Base):
    """股票基本信息表"""
    __tablename__ = "stock_info"

    code = Column(String(10), primary_key=True, comment="股票代码，如 000001")
    name = Column(String(32), nullable=False, comment="股票名称")
    market = Column(String(4), nullable=False, comment="市场代码：SH/SZ/BJ")
    status = Column(String(8), default="active", comment="状态：active/suspended/delisted")
    industry = Column(String(64), default="", comment="所属行业")
    list_date = Column(DateTime, nullable=True, comment="上市日期")
    total_shares = Column(Float, default=0.0, comment="总股本（万股）")
    circulating_shares = Column(Float, default=0.0, comment="流通股本（万股）")
    is_st = Column(Boolean, default=False, comment="是否ST/ST*")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<StockInfo(code={self.code}, name={self.name}, market={self.market})>"


class StockDailyPrice(Base):
    """股票日线价格"""
    __tablename__ = "stock_daily_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, index=True, comment="股票代码")
    trade_date = Column(DateTime, nullable=False, comment="交易日期")
    open_price = Column(Float, nullable=False, comment="开盘价")
    close_price = Column(Float, nullable=False, comment="收盘价")
    high_price = Column(Float, nullable=False, comment="最高价")
    low_price = Column(Float, nullable=False, comment="最低价")
    volume = Column(Float, default=0.0, comment="成交量（手）")
    amount = Column(Float, default=0.0, comment="成交额（万元）")
    pre_close = Column(Float, nullable=True, comment="昨收价")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<DailyPrice(code={self.code}, date={self.trade_date})>"
