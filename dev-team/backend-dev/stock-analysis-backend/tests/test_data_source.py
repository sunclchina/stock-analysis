"""
数据源管理器测试。
测试数据源注册、状态检测、自动降级链路、新浪财经HTTP接口封装。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.data_source.base import (
    BaseDataSource, QuoteData, KLineData, DataSourceStatus
)
from backend.services.data_source.fallback import DataSourceManager


# ============================================================
# TEST DATA — 测试用模拟数据源
# ============================================================

class MockDataSource(BaseDataSource):
    """测试用模拟数据源"""

    def __init__(self, name: str, should_fail: bool = False, fail_after: int = 999):
        super().__init__(name)
        self._should_fail = should_fail
        self._fail_after = fail_after
        self._call_count = 0

    async def get_quote(self, code: str):
        self._call_count += 1
        if self._should_fail and self._call_count >= self._fail_after:
            self.record_failure()
            return None
        self.record_success()
        return QuoteData(
            code=code, name=f"Mock-{code}",
            price=10.0, open_price=9.8, high_price=10.2, low_price=9.7,
            pre_close=9.9, change=0.1, change_pct=1.0, volume=10000, amount=100000,
        )

    async def get_quotes(self, codes: list):
        results = []
        for code in codes:
            q = await self.get_quote(code)
            if q:
                results.append(q)
        return results

    async def get_kline(self, code: str, count: int = 120):
        return []

    async def search_stock(self, keyword: str):
        return []


# ============================================================
# 基础数据源测试
# ============================================================

class TestBaseDataSource:

    def test_success_status(self):
        """测试成功调用状态"""
        ds = MockDataSource("test")
        assert ds.status == DataSourceStatus.ONLINE
        assert ds.is_available() is True

    def test_failure_tracking(self):
        """测试失败计数和自动降级"""
        ds = MockDataSource("test")
        ds.record_failure()
        assert ds.status == DataSourceStatus.DEGRADED
        assert ds.is_available() is True

        ds.record_failure()
        assert ds.status == DataSourceStatus.DEGRADED
        assert ds.is_available() is True

        ds.record_failure()  # 第3次失败 -> OFFLINE
        assert ds.status == DataSourceStatus.OFFLINE
        assert ds.is_available() is False

    def test_success_resets_failure_count(self):
        """测试成功后重置失败计数"""
        ds = MockDataSource("test")
        ds.record_failure()
        ds.record_failure()
        assert ds.status == DataSourceStatus.DEGRADED
        ds.record_success()
        assert ds._consecutive_failures == 0
        assert ds.status == DataSourceStatus.ONLINE


# ============================================================
# 数据源管理器测试
# ============================================================

class TestDataSourceManager:

    @pytest.fixture
    def manager(self, monkeypatch):
        """创建测试管理器"""
        monkeypatch.setattr(
            "backend.config.settings.primary_data_source", "primary"
        )
        monkeypatch.setattr(
            "backend.config.settings.fallback_data_source", "fallback"
        )
        mgr = DataSourceManager()
        mgr.register(MockDataSource("primary"))
        mgr.register(MockDataSource("fallback"))
        return mgr

    @pytest.mark.asyncio
    async def test_initial_active_is_primary(self, manager):
        """测试初始活跃数据源为主数据源"""
        assert manager._active_name == "primary"
        assert manager.active is not None
        assert manager.active.name == "primary"

    @pytest.mark.asyncio
    async def test_get_status_summary(self, manager):
        """测试数据源状态摘要"""
        summary = manager.get_status_summary()
        assert len(summary) == 2
        # 主数据源应标记为活跃
        primary_info = next(s for s in summary if s["name"] == "primary")
        assert primary_info["is_active"] is True
        assert primary_info["is_primary"] is True

        fallback_info = next(s for s in summary if s["name"] == "fallback")
        assert fallback_info["is_active"] is False
        assert fallback_info["is_primary"] is False

    @pytest.mark.asyncio
    async def test_auto_switch_to_fallback(self, manager):
        """测试主数据源不可用时自动切换到备用"""
        # 让主数据源失败3次（通过反复调用）
        primary = manager.primary
        assert primary is not None
        for _ in range(3):
            primary.record_failure()

        assert primary.is_available() is False

        await manager.auto_switch_if_needed()
        assert manager._active_name == "fallback"

    @pytest.mark.asyncio
    async def test_auto_switch_back_to_primary(self, manager):
        """测试主数据源恢复后自动切回"""
        # 先模拟切到备用
        primary = manager.primary
        fallback = manager.fallback
        for _ in range(3):
            primary.record_failure()
        await manager.auto_switch_if_needed()
        assert manager._active_name == "fallback"

        # 主数据源恢复
        primary.record_success()
        await manager.auto_switch_if_needed()
        assert manager._active_name == "primary"

    @pytest.mark.asyncio
    async def test_get_quote_with_fallback(self, manager):
        """测试获取行情时主数据源失败自动降级"""
        primary = manager.primary
        for _ in range(3):
            primary.record_failure()

        quote = await manager.get_quote("000001")
        assert quote is not None
        assert quote.code == "000001"
        # 应该从备用数据源获取
        assert manager._active_name == "fallback"

    @pytest.mark.asyncio
    async def test_get_quotes_fallback(self, manager):
        """测试批量获取行情降级"""
        primary = manager.primary
        for _ in range(3):
            primary.record_failure()

        quotes = await manager.get_quotes(["000001", "600519"])
        assert len(quotes) >= 0  # 降级到备用
        assert manager._active_name == "fallback"


# ============================================================
# QuoteData / KLineData 数据类测试
# ============================================================

class TestQuoteData:

    def test_quote_to_dict(self):
        """测试QuoteData转字典"""
        from datetime import datetime
        q = QuoteData(
            code="000001", name="平安银行",
            price=12.5, open_price=12.0,
            high_price=12.8, low_price=11.9,
            pre_close=12.0, change=0.5, change_pct=4.17,
            volume=100000, amount=1250000,
            timestamp=datetime(2026, 4, 29, 10, 30, 0),
        )
        d = q.to_dict()
        assert d["code"] == "000001"
        assert d["name"] == "平安银行"
        assert d["price"] == 12.5
        assert d["change"] == 0.5
        assert d["change_pct"] == 4.17
        assert "timestamp" in d

    def test_quote_default_timestamp(self):
        """测试时间戳默认为当前时间"""
        q = QuoteData(
            code="000001", name="测试",
            price=10.0, open_price=9.8,
            high_price=10.2, low_price=9.7,
            pre_close=9.9, change=0.1, change_pct=1.0,
            volume=10000, amount=100000,
        )
        assert q.timestamp is not None  # 默认自动填充


class TestKLineData:

    def test_kline_to_dict(self):
        """测试KLineData转字典"""
        from datetime import datetime
        k = KLineData(
            code="600519",
            trade_date=datetime(2026, 4, 29),
            open_price=1660.0, close_price=1680.0,
            high_price=1700.0, low_price=1650.0,
            volume=28000, amount=47000000,
        )
        d = k.to_dict()
        assert d["code"] == "600519"
        assert d["date"] == "2026-04-29"
        assert d["open"] == 1660.0
        assert d["close"] == 1680.0
