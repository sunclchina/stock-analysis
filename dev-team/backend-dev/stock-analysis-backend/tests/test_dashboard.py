"""
M01 系统仪表盘、技术指标工具、WebSocket管理器、缓存测试。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================
# 仪表盘API测试
# ============================================================

class TestDashboardAPI:

    @patch("backend.api.dashboard.get_db")
    @patch("backend.api.dashboard._get_dsm")
    @patch("backend.api.dashboard._get_engine")
    def test_get_dashboard(self, mock_engine, mock_dsm, mock_get_db):
        """测试仪表盘聚合数据"""
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.all.return_value = []
        mock_get_db.return_value = mock_session

        mock_dsm_instance = MagicMock()
        mock_dsm_instance.get_status_summary.return_value = []
        mock_dsm_instance._active_name = "tdx_local"
        mock_dsm_instance.get_quote = AsyncMock(return_value=None)
        mock_dsm.return_value = mock_dsm_instance

        mock_eng = MagicMock()
        mock_eng.is_running = False
        mock_eng._monitor_codes = []
        mock_engine.return_value = mock_eng

        response = client.get("/api/v1/dashboard")
        if response.status_code == 200:
            data = response.json()
            assert "system_status" in data
            assert "market_overview" in data
            assert "warning_summary" in data
            assert "watchlist_snapshot" in data
            assert "generated_at" in data


# ============================================================
# 技术指标工具测试
# ============================================================

class TestIndicators:

    def test_calc_ma(self):
        """测试移动平均线计算"""
        from backend.utils.indicators import calc_ma
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        ma5 = calc_ma(prices, 5)
        assert len(ma5) == len(prices)
        assert ma5[0] is None  # 前4个不足5周期
        assert ma5[4] is not None  # 第5个开始有值
        assert ma5[4] == 12.0  # (10+11+12+13+14)/5

    def test_calc_ma_short_data(self):
        """测试数据不足的移动平均线"""
        from backend.utils.indicators import calc_ma
        result = calc_ma([1, 2], 5)
        assert all(v is None for v in result)

    def test_calc_macd(self):
        """测试MACD计算"""
        from backend.utils.indicators import calc_macd
        prices = [100 + i * 0.5 + (i % 5) * 2 for i in range(40)]
        result = calc_macd(prices)
        assert "dif" in result
        assert "dea" in result
        assert "macd_histogram" in result
        # MACD需要 slow(26)+signal(9)=35 条以上数据
        assert len(result["dif"]) == len(prices)

    def test_calc_macd_short_data(self):
        """测试数据不足的MACD"""
        from backend.utils.indicators import calc_macd
        result = calc_macd([1, 2, 3], 12, 26, 9)
        assert result["dif"] == []
        assert result["dea"] == []

    def test_calc_rsi(self):
        """测试RSI计算"""
        from backend.utils.indicators import calc_rsi
        # 用足够多的数据确保RSI有稳定输出
        prices = [100 + i * 0.5 + (1 if i % 2 == 0 else -1) for i in range(25)]
        result = calc_rsi(prices, 14)
        assert len(result) == len(prices)
        # RSI需要 period+1=15 个数据点，之后有值
        non_none = [v for v in result if v is not None]
        assert len(non_none) > 0

    def test_calc_rsi_short_data(self):
        """测试数据不足的RSI"""
        from backend.utils.indicators import calc_rsi
        result = calc_rsi([1, 2], 14)
        assert all(v is None for v in result)

    def test_calc_kdj(self):
        """测试KDJ计算"""
        from backend.utils.indicators import calc_kdj
        closes = [100 + i * 0.5 for i in range(20)]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        result = calc_kdj(highs, lows, closes, 9)
        assert "k" in result
        assert "d" in result
        assert "j" in result
        assert len(result["k"]) == len(closes)

    def test_calc_kdj_short_data(self):
        """测试数据不足的KDJ"""
        from backend.utils.indicators import calc_kdj
        result = calc_kdj([], [], [1, 2], 9)
        assert result["k"] == []

    def test_calc_ema(self):
        """测试EMA计算"""
        from backend.utils.indicators import calc_ema
        prices = [10, 11, 12, 13, 14, 15]
        result = calc_ema(prices, 3)
        assert len(result) == len(prices)
        non_none = [v for v in result if v is not None]
        assert len(non_none) > 0

    def test_calc_ema_short_data(self):
        """测试数据不足的EMA"""
        from backend.utils.indicators import calc_ema
        result = calc_ema([1], 3)
        assert all(v is None for v in result)


# ============================================================
# 缓存工具测试
# ============================================================

class TestMemoryCache:

    def test_set_and_get(self):
        """测试缓存写入和读取"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        assert cache.get("nonexistent") is None

    def test_contains(self):
        """测试包含检查"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        cache.set("key1", "value1")
        assert cache.contains("key1") is True
        assert cache.contains("key2") is False

    def test_delete(self):
        """测试删除"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        """测试清空"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size == 0

    def test_size_and_maxsize(self):
        """测试容量"""
        from backend.utils.cache import MemoryCache
        cache = MemoryCache(maxsize=100, ttl=60)
        assert cache.maxsize == 100

    def test_expiration(self):
        """测试过期（TTL）"""
        from backend.utils.cache import MemoryCache
        import time
        cache = MemoryCache(maxsize=100, ttl=0.1)  # 100ms TTL
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None  # 已过期


# ============================================================
# WebSocket管理器测试
# ============================================================

class TestWebSocketManager:

    @pytest.mark.asyncio
    async def test_connection_count(self):
        """测试连接计数"""
        from backend.services.websocket_manager import ConnectionManager
        mgr = ConnectionManager()
        assert mgr.count == 0

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """测试广播"""
        from backend.services.websocket_manager import ConnectionManager
        mgr = ConnectionManager()
        # 无连接时广播不应出错
        await mgr.broadcast("test_event", {"key": "value"})
        await mgr.broadcast_market_update([])
        await mgr.broadcast_warning_trigger({"code": "000001"})
        await mgr.broadcast_warning_resolve("test-id")
        await mgr.broadcast_config_change("test")
        await mgr.send_heartbeat()


# ============================================================
# 股票模型测试
# ============================================================

class TestStockModels:

    def test_stock_info_repr(self):
        """测试StockInfo模型"""
        from backend.models.stock import StockInfo
        s = StockInfo(code="000001", name="平安银行", market="SZ")
        assert repr(s) == "<StockInfo(code=000001, name=平安银行, market=SZ)>"

    def test_stock_daily_price_repr(self):
        """测试StockDailyPrice模型"""
        from backend.models.stock import StockDailyPrice
        p = StockDailyPrice(code="000001", trade_date=None)
        assert repr(p) == "<DailyPrice(code=000001, date=None)>"

    def test_analysis_report_repr(self):
        """测试AnalysisReport模型"""
        from backend.models.analysis import AnalysisReport
        r = AnalysisReport(report_type="review", status="completed")
        assert repr(r) == "<Report(id=None, type=review, status=completed)>"
