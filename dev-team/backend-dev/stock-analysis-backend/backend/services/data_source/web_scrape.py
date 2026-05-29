"""
网页爬取数据源（应急备用数据源）。
当所有其他数据源不可用时，尝试从公开财经网站抓取数据。
使用 httpx 直接请求新浪财经、东方财富等公开页面。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import re

import httpx

from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData

logger = logging.getLogger(__name__)


class WebScrapeDataSource(BaseDataSource):
    """网页爬取应急数据源"""

    def __init__(self):
        super().__init__(name="web_scrape")

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """从新浪财经抓取单只股票行情"""
        try:
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            prefix = "sh" if clean.startswith(("6", "9")) else "sz"
            if clean in ("000001", "000300", "000016", "000688", "000905"):
                prefix = "sh"
            url = f"https://hq.sinajs.cn/list={prefix}{clean}"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url, headers={"Referer": "https://finance.sina.com.cn"})
                text = r.content.decode("gbk", errors="ignore")
            start = text.find('"')
            end = text.rfind('"')
            if start == -1 or end == -1:
                self.record_failure()
                return None
            parts = text[start + 1:end].split(",")
            if len(parts) < 33:
                self.record_failure()
                return None
            name = parts[0]
            price = float(parts[3]) if parts[3] else 0.0
            pre_close = float(parts[2]) if parts[2] else 0.0
            open_price = float(parts[1]) if parts[1] else 0.0
            high = float(parts[4]) if parts[4] else 0.0
            low = float(parts[5]) if parts[5] else 0.0
            volume = float(parts[8]) if parts[8] else 0.0
            amount = float(parts[9]) if parts[9] else 0.0
            change = price - pre_close
            change_pct = (change / pre_close * 100) if pre_close != 0 else 0.0
            self.record_success()
            return QuoteData(
                code=clean, name=name,
                price=round(price, 2), open_price=round(open_price, 2),
                high_price=round(high, 2), low_price=round(low, 2),
                pre_close=round(pre_close, 2),
                change=round(change, 2), change_pct=round(change_pct, 2),
                volume=volume, amount=amount,
            )
        except Exception as e:
            logger.warning(f"WebScrape quote failed: {e}")
            self.record_failure()
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量抓取（逐个请求）"""
        results = []
        for code in codes:
            q = await self.get_quote(code)
            if q:
                results.append(q)
        return results

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """从新浪获取K线数据（应急）"""
        try:
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            prefix = "sh" if clean.startswith(("6", "9")) else "sz"
            url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={prefix}{clean}&scale=240&datalen={count}"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(url)
                data = r.json()
            results = []
            for item in data:
                try:
                    dt = datetime.strptime(item.get("date", ""), "%Y-%m-%d")
                except (ValueError, TypeError):
                    continue
                results.append(KLineData(
                    code=clean, trade_date=dt,
                    open_price=float(item.get("open", 0)),
                    close_price=float(item.get("close", 0)),
                    high_price=float(item.get("high", 0)),
                    low_price=float(item.get("low", 0)),
                    volume=float(item.get("volume", 0)),
                    amount=float(item.get("amount", 0)),
                ))
            if results:
                self.record_success()
            else:
                self.record_failure()
            return results
        except Exception as e:
            logger.warning(f"WebScrape kline failed: {e}")
            self.record_failure()
            return []

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """网页爬取不支持搜索"""
        return []
