"""
新浪财经数据源（备用数据源）。
通过新浪免费行情接口获取实时行情数据。

遵循架构方案：备用数据源，在主数据源 (tdx_local) 不可用时自动切换。
"""

from typing import List, Optional, Dict, Any
import httpx

from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData


# ── 新浪分时数据 API（1分钟粒度）
SINA_TIMESHARE_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=1&datalen=240"


# 新浪行情接口URL模板
# 新浪行情接口URL模板
# 注意：新浪接口需要 sh/sz 市场前缀
SINA_QUOTE_URL = "https://hq.sinajs.cn/list={codes}"
SINA_KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&datalen={count}"

# 已知指数代码 → 新浪前缀
# 部分指数（如上证50、沪深300等）代码以0开头但在上海交易所
SINA_INDEX_PREFIX: dict = {
    "000001": "sh",  # 上证指数
    "000688": "sh",  # 科创50
    "000300": "sh",  # 沪深300
    "000016": "sh",  # 上证50
    "000905": "sh",  # 中证500
    "899050": "bj",  # 北证50
    "899601": "bj",  # 北证专精特新
}

# 股票代码 -> 新浪市场前缀
# sh=上海(6xx), sz=深圳(0xx/3xx/002xx)
def to_sina_code(code: str) -> str:
    """将纯数字股票代码转换为新浪格式（带sh/sz前缀）"""
    clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    # 先检查是否已知指数
    if clean in SINA_INDEX_PREFIX:
        return f"{SINA_INDEX_PREFIX[clean]}{clean}"
    # 股票代码判断
    if clean.startswith(("6", "9")):
        return f"sh{clean}"
    else:
        return f"sz{clean}"


class SinaDataSource(BaseDataSource):
    """新浪财经实时行情数据源"""

    def __init__(self):
        super().__init__(name="sina")
        self._client = None  # 延迟创建

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx 客户端（延迟创建，事件循环变更时自动重建）"""
        if self._client is not None:
            try:
                import asyncio
                _ = asyncio.get_running_loop()
                _ = self._client.is_closed
            except (RuntimeError, Exception):
                self._client = None
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                follow_redirects=True,
            )
        return self._client

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """获取单只股票行情（通过新浪接口，自动加sh/sz前缀）"""
        sina_code = to_sina_code(code)
        url = SINA_QUOTE_URL.format(codes=sina_code)
        clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        try:
            client = await self._get_client()
            response = await client.get(url, headers={"Referer": "https://finance.sina.com.cn"})
            response.raise_for_status()
            # GBK解码
            raw = response.content
            try:
                text = raw.decode("gbk")
            except (UnicodeDecodeError, AttributeError):
                text = response.text
            if not text or '=""' in text:
                self.record_failure()
                return None

            parsed = self._parse_sina_response(text, clean_code)
            if parsed:
                self.record_success()
                return parsed
            self.record_failure()
            return None
        except (httpx.HTTPError, httpx.TimeoutException):
            self.record_failure()
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量获取行情（新浪格式需带sh/sz前缀）"""
        sina_codes = [to_sina_code(c) for c in codes]
        codes_str = ",".join(sina_codes)
        url = SINA_QUOTE_URL.format(codes=codes_str)
        results = []
        code_to_clean = {to_sina_code(c): c for c in codes}

        try:
            client = await self._get_client()
            response = await client.get(url, headers={"Referer": "https://finance.sina.com.cn"})
            response.raise_for_status()
            # 新浪返回GBK编码，强制用GBK解码
            raw = response.content
            try:
                text = raw.decode("gbk")
            except (UnicodeDecodeError, AttributeError):
                text = response.text
            lines = text.strip().split("\n")
            for line in lines:
                for sina_code, clean_code in code_to_clean.items():
                    if sina_code in line:
                        parsed = self._parse_sina_response(line, clean_code)
                        if parsed:
                            results.append(parsed)
                            break
            self.record_success()
        except (httpx.HTTPError, httpx.TimeoutException):
            self.record_failure()

        return results

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """获取K线数据（新浪需要 sh/sz 前缀）"""
        sina_code = to_sina_code(code)
        url = SINA_KLINE_URL.format(code=sina_code, count=count)
        results = []
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            for item in data:
                results.append(
                    KLineData(
                        code=code,
                        trade_date=item.get("date", ""),
                        open_price=float(item.get("open", 0)),
                        close_price=float(item.get("close", 0)),
                        high_price=float(item.get("high", 0)),
                        low_price=float(item.get("low", 0)),
                        volume=float(item.get("volume", 0)),
                        amount=float(item.get("amount", 0)),
                    )
                )
            self.record_success()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError):
            self.record_failure()
        return results

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """新浪不支持模糊搜索，返回空列表"""
        return []

    async def get_timeshare(self, code: str) -> List[Dict[str, Any]]:
        """
        获取今日分时数据（1分钟粒度）。
        通过新浪1分钟K线接口获取，行情时段约为9:30~15:00共240条。
        """
        clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        sina_code = to_sina_code(code)
        url = SINA_TIMESHARE_URL.format(code=sina_code)
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            if not data or not isinstance(data, list):
                self.record_failure()
                return []
            result = []
            for item in data:
                result.append({
                    "time": item.get("date", ""),
                    "price": float(item.get("close", 0)),
                    "avg_price": float(item.get("avg", 0)) if item.get("avg") else 0,
                    "volume": float(item.get("volume", 0)),
                    "amount": float(item.get("amount", 0)),
                })
            self.record_success()
            return result
        except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError, TypeError):
            self.record_failure()
            return []

    @staticmethod
    def _parse_sina_response(text: str, code: str) -> Optional[QuoteData]:
        """解析新浪返回的JS格式行情数据"""
        try:
            # 新浪格式：var hq_str_sh000001="上证指数,3210.10,3208.51,..."
            start = text.find('"')
            end = text.rfind('"')
            if start == -1 or end == -1:
                return None
            parts = text[start + 1 : end].split(",")
            if len(parts) < 33:
                return None

            name = parts[0]
            open_price = float(parts[1]) if parts[1] else 0.0
            pre_close = float(parts[2]) if parts[2] else 0.0
            price = float(parts[3]) if parts[3] else 0.0
            high_price = float(parts[4]) if parts[4] else 0.0
            low_price = float(parts[5]) if parts[5] else 0.0
            volume = float(parts[8]) if parts[8] else 0.0  # 成交量(股)
            amount = float(parts[9]) if parts[9] else 0.0   # 成交额(元)

            change = price - pre_close if pre_close != 0 else 0.0
            change_pct = (change / pre_close * 100) if pre_close != 0 else 0.0

            return QuoteData(
                code=code,
                name=name,
                price=price,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                pre_close=pre_close,
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=volume,
                amount=amount,
            )
        except (ValueError, IndexError):
            return None
