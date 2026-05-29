"""
东方财富数据源（备用数据源）。
通过东方财富公开API获取实时行情和K线数据。

API端点（URL从 settings 读取，可配置不硬编码）：
- 批量行情：push2.eastmoney.com/api/qt/ulist.np/get
- 单只行情：push2.eastmoney.com/api/qt/stock/get
- K线数据：push2his.eastmoney.com/api/qt/stock/kline/get

遵循原则②：URL 可配置；原则③：按架构方案实现。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from backend.config.settings import settings
from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData

# ── 指数代码 → EastMoney secid 映射 ──────────────────────────────
# East Money 用 "market.code" 作为 secid，market=1 为上海，market=0 为深圳
INDEX_MAP: Dict[str, tuple] = {
    "000001": (1, "上证指数"),
    "399001": (0, "深证成指"),
    "399006": (0, "创业板指"),
    "000688": (1, "科创50"),
    "000300": (1, "沪深300"),
    "000016": (1, "上证50"),
    "000905": (1, "中证500"),
    "000852": (1, "中证1000"),
    "399673": (0, "创业板50"),
    "399005": (0, "中小100"),
}


def code_to_secid(code: str) -> str:
    """
    将股票/指数代码转换为 East Money secid 格式 "market.code"。

    指数走 INDEX_MAP 映射，股票按代码前缀判断：
    - 6xxxxx → 上海 (market=1)
    - 0xxxxx, 3xxxxx, 002xxx, 001xxx, 4xxxxx, 8xxxxx → 深圳 (market=0)
    """
    # 去除可能的后缀 .SH, .SZ, .BJ
    clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

    # 先检查是否已知指数
    if clean_code in INDEX_MAP:
        market, _ = INDEX_MAP[clean_code]
        return f"{market}.{clean_code}"

    # 股票代码判断
    if clean_code.startswith("6"):
        return f"1.{clean_code}"
    elif clean_code.startswith(("0", "3", "002", "001", "4", "8")):
        return f"0.{clean_code}"
    else:
        # 默认当做上海市场
        return f"1.{clean_code}"


# ── API 响应字段常量 ──────────────────────────────────────────────
# 批量行情 fields: f2=最新价, f3=涨跌幅, f4=涨跌额, f5=成交量(手), f6=成交额, f7=振幅%, f8=换手率%, f12=代码, f14=名称
# 注意：f168(换手率)在列表API(ulist.np/get)中不可用，改用f8
QUOTE_BATCH_FIELDS = "f2,f3,f4,f5,f6,f7,f8,f12,f14"
# 单只行情额外 fields: f15=最高, f16=最低, f17=今开, f18=昨收, f168=换手率%(仅在详情API可用)
QUOTE_FULL_FIELDS = "f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18,f168"


class EastMoneyDataSource(BaseDataSource):
    """东方财富实时行情数据源"""

    def __init__(self):
        super().__init__(name="eastmoney")
        self._timeout = settings.eastmoney_timeout
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/",
        }
        self._client = httpx.AsyncClient(timeout=self._timeout, headers=self._headers)
        # 请求计数器
        self.success_count = 0
        self.failure_count = 0

    # ── 行情接口 ──────────────────────────────────────────────────

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """获取单只股票/指数实时行情"""
        secid = code_to_secid(code)
        url = settings.eastmoney_single_quote_url
        params = {
            "fltt": "2",
            "secid": secid,
            "fields": QUOTE_FULL_FIELDS,
        }
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            quote = self._parse_single_quote(data, code)
            if quote:
                self.record_success()
                self.success_count += 1
                return quote

            self.record_failure()
            self.failure_count += 1
            return None
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
            self.record_failure()
            self.failure_count += 1
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量获取股票/指数实时行情（一次请求多条），失败自动重试一次"""
        for attempt in range(2):
            results = await self._get_quotes_once(codes)
            if results:
                return results
            # 第一次失败：短暂等待后重试
            if attempt == 0:
                import asyncio
                await asyncio.sleep(0.5)
        return []

    async def _get_quotes_once(self, codes: List[str]) -> List[QuoteData]:
        """单次批量查询"""
        secid_list = [code_to_secid(c) for c in codes]
        secids = ",".join(secid_list)
        url = settings.eastmoney_batch_quote_url
        params = {
            "fltt": "2",
            "fields": QUOTE_BATCH_FIELDS,
            "secids": secids,
        }

        results: List[QuoteData] = []

        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data or "data" not in data or "diff" not in data["data"]:
                self.record_failure()
                self.failure_count += 1
                return results

            diff = data["data"]["diff"]
            if not isinstance(diff, list):
                diff = [diff]

            for item in diff:
                quote = self._parse_batch_item(item)
                if quote:
                    results.append(quote)

            if results:
                self.record_success()
                self.success_count += 1
            else:
                self.record_failure()
                self.failure_count += 1
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
            self.record_failure()
            self.failure_count += 1

        return results

    # ── K线接口 ───────────────────────────────────────────────────

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """获取K线数据"""
        secid = code_to_secid(code)
        url = settings.eastmoney_kline_url
        params = {
            "secid": secid,
            "klt": "101",       # 101=日K, 102=周, 103=月
            "fqt": "1",         # 1=前复权, 0=不复权
            "lmt": str(count),
        }

        results: List[KLineData] = []

        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data or "data" not in data or "klines" not in data["data"]:
                self.record_failure()
                self.failure_count += 1
                return results

            klines = data["data"]["klines"]
            for raw_line in klines:
                kline = self._parse_kline_line(code, raw_line)
                if kline:
                    results.append(kline)

            if results:
                self.record_success()
                self.success_count += 1
            else:
                self.record_failure()
                self.failure_count += 1
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
            self.record_failure()
            self.failure_count += 1

        return results

    # ── 搜索接口 ──────────────────────────────────────────────────

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """
        搜索股票（通过东财搜索API）。
        使用 East Money 搜索接口：https://searchadapter.eastmoney.com/api/suggest/get
        """
        search_url = (
            "https://searchadapter.eastmoney.com/api/suggest/get"
        )
        params = {
            "input": keyword,
            "type": 14,       # 全类型（股票+基金+指数）
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": 10,
        }

        results: List[Dict[str, str]] = []

        try:
            resp = await self._client.get(search_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data or "QuotationCodeTable" not in data:
                return results

            items = data["QuotationCodeTable"].get("Data", [])
            for item in items:
                code = item.get("Code", "")
                name = item.get("Name", "")
                if code and name:
                    results.append({"code": code, "name": name})

            if results:
                self.record_success()
                self.success_count += 1
            else:
                self.record_failure()
                self.failure_count += 1
        except (httpx.HTTPError, httpx.TimeoutException, ValueError) as e:
            self.record_failure()
            self.failure_count += 1

        return results

    # ── 内部解析 ──────────────────────────────────────────────────

    @staticmethod
    def _parse_single_quote(data: dict, code: str) -> Optional[QuoteData]:
        """解析单只行情API返回的 JSON"""
        if not data or "data" not in data:
            return None

        d = data["data"]
        if d is None:
            return None

        f2 = d.get("f2")   # 最新价
        f3 = d.get("f3")   # 涨跌幅
        f4 = d.get("f4")   # 涨跌额
        f5 = d.get("f5")   # 成交量(手)
        f6 = d.get("f6")   # 成交额
        f7 = d.get("f7")   # 振幅%
        f12 = d.get("f12") or code  # 代码
        f14 = d.get("f14") or ""     # 名称
        f15 = d.get("f15")  # 最高
        f16 = d.get("f16")  # 最低
        f17 = d.get("f17")  # 今开
        f18 = d.get("f18")  # 昨收
        f168 = d.get("f168")  # 换手率%

        if f2 is None:
            return None

        price = float(f2)
        pre_close = float(f18) if f18 is not None else 0.0
        open_price = float(f17) if f17 is not None else 0.0
        high = float(f15) if f15 is not None else 0.0
        low = float(f16) if f16 is not None else 0.0
        volume = float(f5) if f5 is not None else 0.0
        amount = float(f6) if f6 is not None else 0.0
        change = float(f4) if f4 is not None else (price - pre_close)
        change_pct = float(f3) if f3 is not None else (change / pre_close * 100 if pre_close != 0 else 0.0)
        turnover_rate = float(f168) if f168 is not None else 0.0
        amplitude = float(f7) if f7 is not None else 0.0

        return QuoteData(
            code=f12,
            name=f14,
            price=round(price, 2),
            open_price=round(open_price, 2),
            high_price=round(high, 2),
            low_price=round(low, 2),
            pre_close=round(pre_close, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=volume,
            amount=amount,
            turnover_rate=round(turnover_rate, 2),
            amplitude=round(amplitude, 2),
        )

    @staticmethod
    def _parse_single_quote_extra(item: dict) -> tuple:
        """从详情API中解析换手率和振幅"""
        f168 = item.get("f168")
        f7 = item.get("f7")
        tr = float(f168) if f168 is not None else 0.0
        amp = float(f7) if f7 is not None else 0.0
        return tr, amp

    @staticmethod
    def _parse_batch_item(item: dict) -> Optional[QuoteData]:
        """解析批量行情API中一条记录的 JSON"""
        f2 = item.get("f2")   # 最新价
        f3 = item.get("f3")   # 涨跌幅
        f4 = item.get("f4")   # 涨跌额
        f5 = item.get("f5")   # 成交量(手)
        f6 = item.get("f6")   # 成交额
        f7 = item.get("f7")   # 振幅%
        f8 = item.get("f8")   # 换手率%（列表API用f8，详情API用f168）
        f12 = item.get("f12") or ""  # 代码
        f14 = item.get("f14") or ""  # 名称

        if f2 is None or not f12:
            return None

        price = float(f2)
        change = float(f4) if f4 is not None else 0.0
        change_pct = float(f3) if f3 is not None else 0.0
        volume = float(f5) if f5 is not None else 0.0
        amount = float(f6) if f6 is not None else 0.0
        turnover_rate = float(f8) if f8 is not None else 0.0
        amplitude = float(f7) if f7 is not None else 0.0

        return QuoteData(
            code=f12,
            name=f14,
            price=round(price, 2),
            open_price=0.0,
            high_price=0.0,
            low_price=0.0,
            pre_close=0.0,
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=volume,
            amount=amount,
            turnover_rate=round(turnover_rate, 2),
            amplitude=round(amplitude, 2),
        )

    @staticmethod
    def _parse_kline_line(code: str, raw: str) -> Optional[KLineData]:
        """
        解析一条K线文本行。
        东财 Kline 格式：日,开盘,收盘,最高,最低,成交量(手),成交额(元),振幅,涨跌幅,涨跌额,换手率
        """
        parts = raw.split(",")
        if len(parts) < 7:
            return None

        try:
            date_str = parts[0].strip()
            trade_date = datetime.strptime(date_str, "%Y-%m-%d")
            open_price = float(parts[1])
            close_price = float(parts[2])
            high_price = float(parts[3])
            low_price = float(parts[4])
            volume = float(parts[5])  # 成交量(手)
            amount = float(parts[6])  # 成交额(元)

            return KLineData(
                code=code,
                trade_date=trade_date,
                open_price=open_price,
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
                volume=volume,
                amount=amount,
            )
        except (ValueError, IndexError):
            return None
