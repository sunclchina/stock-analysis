"""
M02 实时行情模块API测试。
测试大盘概览、批量行情、K线数据接口。
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.data_source.base import QuoteData, KLineData
from datetime import datetime

client = TestClient(app)


class TestMarketAPI:

    @patch("backend.api.market._get_dsm")
    def test_market_overview(self, mock_get_dsm):
        """测试大盘概览接口"""
        mock_dsm = MagicMock()
        mock_dsm._active_name = "tdx_local"

        mock_quote = QuoteData(
            code="000001.SH", name="上证指数",
            price=3200.0, open_price=3190.0,
            high_price=3210.0, low_price=3185.0,
            pre_close=3190.0, change=10.0, change_pct=0.31,
            volume=200000000, amount=3000000000,
        )

        async def mock_get_quote(code):
            return mock_quote

        mock_dsm.get_quote = mock_get_quote
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/overview")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "active_data_source" in data
        assert data["active_data_source"] == "tdx_local"

    @patch("backend.api.market._get_dsm")
    def test_batch_quotes(self, mock_get_dsm):
        """测试批量行情接口"""
        mock_dsm = MagicMock()
        mock_dsm._active_name = "tdx_local"

        async def mock_get_quotes(codes):
            return [
                QuoteData(code=c, name=f"Stock-{c}",
                          price=10.0, open_price=9.8, high_price=10.2, low_price=9.7,
                          pre_close=9.9, change=0.1, change_pct=1.0,
                          volume=10000, amount=100000)
                for c in codes
            ]

        mock_dsm.get_quotes = mock_get_quotes
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/quotes/000001%2C600519")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["quotes"]) == 2

    @patch("backend.api.market._get_dsm")
    def test_batch_quotes_empty(self, mock_get_dsm):
        """测试空列表批量行情"""
        response = client.get("/api/v1/market/quotes/")
        assert response.status_code in (200, 404)

    @patch("backend.api.market._get_dsm")
    def test_get_kline(self, mock_get_dsm):
        """测试K线数据接口"""
        mock_dsm = MagicMock()
        mock_dsm._active_name = "tdx_local"

        async def mock_get_kline(code, count=120):
            klines = []
            for i in range(count):
                klines.append(KLineData(
                    code=code,
                    trade_date=datetime(2026, 3, 1 + i),
                    open_price=10.0 + i * 0.1,
                    close_price=10.1 + i * 0.1,
                    high_price=10.2 + i * 0.1,
                    low_price=9.9 + i * 0.1,
                    volume=10000 + i * 100,
                    amount=100000 + i * 1000,
                ))
            return klines

        mock_dsm.get_kline = mock_get_kline
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/kline/000001?count=5")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "000001"
        assert len(data["klines"]) == 5
        assert "period" in data

    @patch("backend.api.market._get_dsm")
    def test_get_single_quote(self, mock_get_dsm):
        """测试单只股票行情接口"""
        mock_dsm = MagicMock()
        mock_dsm._active_name = "tdx_local"

        async def mock_get_quote(code):
            return QuoteData(
                code=code, name="平安银行",
                price=12.5, open_price=12.0, high_price=12.8, low_price=11.9,
                pre_close=12.0, change=0.5, change_pct=4.17,
                volume=100000, amount=1250000,
            )

        mock_dsm.get_quote = mock_get_quote
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/quote/000001")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "000001"
        assert data["name"] == "平安银行"
        assert data["price"] == 12.5

    @patch("backend.api.market._get_dsm")
    def test_get_quote_not_found(self, mock_get_dsm):
        """测试股票行情不可用"""
        mock_dsm = MagicMock()
        async def mock_get_quote(code):
            return None
        mock_dsm.get_quote = mock_get_quote
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/quote/999999")
        assert response.status_code == 404

    @patch("backend.api.market._get_dsm")
    def test_premarket_overview(self, mock_get_dsm):
        """测试盘前提示概览接口"""
        mock_dsm = MagicMock()
        mock_dsm._active_name = "tdx_local"

        async def mock_get_quote(code):
            return QuoteData(
                code=code, name="指数",
                price=3200, open_price=3190, high_price=3210, low_price=3185,
                pre_close=3190, change=10, change_pct=0.31,
                volume=100000, amount=1000000,
            )

        mock_dsm.get_quote = mock_get_quote
        mock_get_dsm.return_value = mock_dsm

        response = client.get("/api/v1/market/premarket")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "is_ai_generated" in data
