"""
数据源抽象基类。
定义统一的数据源接口，所有数据源适配器必须继承此类。

遵循架构方案第七节7.3：
- 连续3次失败自动标记不可用
- 所有数据源通过管理器统一调度
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class QuoteData:
    """行情快照数据"""
    code: str
    name: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    pre_close: float
    change: float           # 涨跌额
    change_pct: float       # 涨跌幅(%)
    volume: float           # 成交量(手)
    amount: float           # 成交额(万元)
    turnover_rate: float = 0.0   # 换手率(%)
    amplitude: float = 0.0       # 振幅(%)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "pre_close": self.pre_close,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "amount": self.amount,
            "turnover_rate": self.turnover_rate,
            "amplitude": self.amplitude,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class KLineData:
    """K线数据"""
    code: str
    trade_date: datetime
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    volume: float
    amount: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "date": self.trade_date.strftime("%Y-%m-%d"),
            "open": self.open_price,
            "close": self.close_price,
            "high": self.high_price,
            "low": self.low_price,
            "volume": self.volume,
            "amount": self.amount,
        }


class DataSourceStatus:
    """数据源状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class BaseDataSource(ABC):
    """
    数据源抽象基类。
    所有具体数据源适配器（通达信、新浪、东方财富等）必须实现此接口。
    """

    def __init__(self, name: str):
        self.name = name
        self._status = DataSourceStatus.ONLINE
        self._consecutive_failures = 0
        self._max_failures = 10  # 连续失败阈值（网络波动容忍度）
        self._failure_window_seconds = 300  # 5分钟滑动窗口：超过此时间无失败则重置计数
        self._last_failure_time = None

    @property
    def status(self) -> str:
        return self._status

    @abstractmethod
    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """获取单只股票实时行情"""
        ...

    @abstractmethod
    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量获取实时行情"""
        ...

    @abstractmethod
    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """获取K线数据"""
        ...

    @abstractmethod
    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """搜索股票"""
        ...

    def record_success(self):
        """记录一次成功调用，重置失败计数并恢复在线状态"""
        self._consecutive_failures = 0
        self._status = DataSourceStatus.ONLINE
        self._last_failure_time = None

    def record_failure(self):
        """
        记录一次失败调用。

        带滑动窗口机制：
        - 如果距上次失败超过 _failure_window_seconds（默认5分钟），重置计数器再累加
        - 连续失败达到 _max_failures（默认10次）标记为 OFFLINE
        - 否则标记为 DEGRADED
        """
        now = datetime.now()

        # 滑动窗口：距上次失败超过窗口期，重置计数（避免隔夜/跨日累计）
        if (self._last_failure_time is not None and
                (now - self._last_failure_time).total_seconds() > self._failure_window_seconds):
            self._consecutive_failures = 0

        self._consecutive_failures += 1
        self._last_failure_time = now

        if self._consecutive_failures >= self._max_failures:
            self._status = DataSourceStatus.OFFLINE
        else:
            self._status = DataSourceStatus.DEGRADED

    def is_available(self) -> bool:
        """
        检查数据源是否可用（含自动恢复逻辑）。

        自动恢复：如果状态为 OFFLINE 但距上次失败已超过窗口期，
        自动降级为 DEGRADED（保留一半失败计数避免立刻再次下线）。
        """
        if self._status == DataSourceStatus.OFFLINE:
            if self._last_failure_time is not None:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed > self._failure_window_seconds:
                    # 自动恢复为 DEGRADED（保留部分计数，避免立刻又下线）
                    self._status = DataSourceStatus.DEGRADED
                    self._consecutive_failures = max(1, self._consecutive_failures // 2)
        return self._status != DataSourceStatus.OFFLINE

    def __repr__(self):
        return f"<DataSource(name={self.name}, status={self._status})>"
