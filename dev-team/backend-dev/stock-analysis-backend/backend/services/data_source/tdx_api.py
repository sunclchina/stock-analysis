"""
TDX 通达信 API 数据源适配器（含财务数据增强）。

通过部署的 TDX API 服务（HTTP REST）获取实时行情、K线等数据。
财务数据（风险评分、财务等级等）从东方财富补齐。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

import httpx

from backend.config.settings import settings
from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData
from backend.services.data_source.eastmoney import EastMoneyDataSource


class TdxApiDataSource(BaseDataSource):
    """基于 HTTP API 的 TDX 数据源（适配已部署的 tdx-api 服务）
    
    行情/K线数据通过 TDX API 获取（低延迟）。
    财务数据通过 EastMoney 补齐（仅用于选股风控评分）。
    """

    def __init__(self):
        super().__init__(name="tdx_api")
        self._base_url = settings.tdx_api_url
        self._client = httpx.AsyncClient(timeout=10.0)
        # 内嵌 EastMoney 用于补财务数据
        self._finance_source = EastMoneyDataSource()
        self.success_count = 0
        self.failure_count = 0

    # ── 行情 ───────────────────────────────────────────

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        url = f"{self._base_url}/api/quote"
        try:
            resp = await self._client.get(url, params={"code": code})
            resp.raise_for_status()
            data = resp.json()
            return self._parse_quote(data, code)
        except Exception:
            self.record_failure()
            self.failure_count += 1
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        results = []
        for code in codes:
            q = await self.get_quote(code)
            if q:
                results.append(q)
        if results:
            self.record_success()
            return results
        return []

    def _parse_quote(self, data: dict, code: str) -> Optional[QuoteData]:
        try:
            price = float(data.get("Price", 0))
            pre_close = float(data.get("YesterdayTD", 0))
            if price == 0 and pre_close == 0:
                return None
            name = str(data.get("Name", code))
            open_price = float(data.get("Open", pre_close))
            high = float(data.get("High", price))
            low = float(data.get("Low", price))
            volume = float(data.get("Volume", 0))
            amount = float(data.get("Amount", 0))
            change_pct = round((price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0.0
            change = price - pre_close
            return QuoteData(
                code=code, name=name, price=price,
                open_price=open_price, high_price=high, low_price=low,
                pre_close=pre_close, change=round(change, 2),
                change_pct=change_pct, volume=volume,
                amount=round(amount / 10000, 2),
            )
        except (ValueError, TypeError):
            return None

    # ── K线 ───────────────────────────────────────────

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        url = f"{self._base_url}/api/kline"
        try:
            resp = await self._client.get(url, params={
                "code": code, "type": "day", "count": count,
            })
            resp.raise_for_status()
            items = resp.json()
            results = []
            for item in items:
                k = self._parse_kline(item, code)
                if k:
                    results.append(k)
            if results:
                self.record_success()
                return results
            return []
        except Exception:
            self.record_failure()
            self.failure_count += 1
            return []

    def _parse_kline(self, item: dict, code: str) -> Optional[KLineData]:
        try:
            date_str = item.get("Date", "")
            trade_date = datetime.fromisoformat(date_str) if isinstance(date_str, str) else datetime.now()
            close = float(item.get("Last", 0))
            if close == 0:
                return None
            return KLineData(
                code=code, trade_date=trade_date,
                open_price=float(item.get("Open", 0)),
                close_price=close,
                high_price=float(item.get("High", 0)),
                low_price=float(item.get("Low", 0)),
                volume=float(item.get("Volume", 0)),
                amount=float(item.get("Amount", 0)),
            )
        except (ValueError, TypeError):
            return None

    # ── 搜索 ───────────────────────────────────────────

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        url = f"{self._base_url}/api/search"
        try:
            resp = await self._client.get(url, params={"keyword": keyword})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [
                    {"code": str(item.get("code", item.get("Code", ""))),
                     "name": str(item.get("name", item.get("Name", ""))),
                     "exchange": str(item.get("exchange", ""))}
                    for item in data
                ]
            return []
        except Exception:
            return []
