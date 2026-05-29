"""
通达信本地数据源解析器。
读取 ds_stk.dat（通达信缓存行情文件）和 .day（日线文件）。

文件格式参考：
- ds_stk.dat：通达信盘后数据缓存文件，固定记录长度
- vipdoc/.../*.day：日线数据文件，每记录32字节

遵循原则②：路径从 settings 读取，不硬编码。
"""

import struct
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from backend.config.settings import settings
from backend.services.data_source.base import (
    BaseDataSource,
    QuoteData,
    KLineData,
)


# 通达信 ds_stk.dat 文件记录结构 (典型)
# 每条记录约 306 字节
DS_STK_RECORD_SIZE = 306
DS_STK_HEADER_SIZE = 0x98  # 文件头偏移

# 日线 .day 文件记录结构 (标准)
# 每记录 32 字节
DAY_RECORD_SIZE = 32


class TDXLocalDataSource(BaseDataSource):
    """
    通达信本地数据源。
    直接从通达信本地缓存文件（ds_stk.dat, *.day）读取行情数据。
    """

    def __init__(self):
        super().__init__(name="tdx_local")
        self._data_dir = settings.tdx_data_dir

    def _find_ds_stk_path(self) -> Optional[str]:
        """查找 ds_stk.dat 文件路径"""
        search_paths = [
            self._data_dir,
            os.path.join(self._data_dir, "T0002", "hq_cache"),
            os.path.join(self._data_dir, "vipdoc"),
        ]
        for base in search_paths:
            path = os.path.join(base, "ds_stk.dat")
            if os.path.isfile(path):
                return path
        return None

    def _parse_ds_stk_record(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解析 ds_stk.dat 中的单条行情记录。

        典型偏移（不同通达信版本有差异）：
        0x00-0x05: 市场代码 + 股票代码 (6 bytes)
        0x08-0x0C: 最新价 (float)
        0x0E-0x12: 昨收 (float)
        0x14-0x18: 开盘 (float)
        0x1C-0x20: 最高 (float)
        0x24-0x28: 最低 (float)
        0x2C-0x30: 成交量 (float?)
        0x30-0x34: 成交额 (float?)
        0x4C-0x50: 股票名称 (8 bytes GBK)
        """
        if len(data) < DS_STK_RECORD_SIZE:
            return None

        try:
            # 股票代码 (6 bytes, 含市场标识)
            code_bytes = data[0:6]
            code = code_bytes.decode("gbk", errors="ignore").strip(" \x00")

            # 股票名称 (8 bytes, GBK编码)
            name_bytes = data[0x4C:0x54]
            name = name_bytes.decode("gbk", errors="ignore").strip(" \x00")

            # 价格相关 (float, 小端)
            if len(data) >= 0x30:
                price = struct.unpack("<f", data[0x08:0x0C])[0]
                pre_close = struct.unpack("<f", data[0x0E:0x12])[0]
                open_price = struct.unpack("<f", data[0x14:0x18])[0]
                high = struct.unpack("<f", data[0x1C:0x20])[0]
                low = struct.unpack("<f", data[0x24:0x28])[0]
                volume = struct.unpack("<f", data[0x2C:0x30])[0]  # 成交量手
                amount = 0.0
                if len(data) >= 0x34:
                    amount = struct.unpack("<f", data[0x30:0x34])[0]

                change = price - pre_close if pre_close != 0 else 0.0
                change_pct = (change / pre_close * 100) if pre_close != 0 else 0.0

                return {
                    "code": code,
                    "name": name,
                    "price": round(price, 2),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "pre_close": round(pre_close, 2),
                    "volume": volume,
                    "amount": amount,
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                }
        except (struct.error, UnicodeDecodeError):
            return None

        return None

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """从 ds_stk.dat 读取单只股票行情"""
        file_path = self._find_ds_stk_path()
        if not file_path:
            self.record_failure()
            return None

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # 跳过文件头，遍历记录
            offset = DS_STK_HEADER_SIZE
            while offset + DS_STK_RECORD_SIZE <= len(data):
                record = data[offset : offset + DS_STK_RECORD_SIZE]
                parsed = self._parse_ds_stk_record(record)
                if parsed and parsed["code"] == code:
                    self.record_success()
                    return QuoteData(
                        code=parsed["code"],
                        name=parsed["name"],
                        price=parsed["price"],
                        open_price=parsed["open"],
                        high_price=parsed["high"],
                        low_price=parsed["low"],
                        pre_close=parsed["pre_close"],
                        change=parsed["change"],
                        change_pct=parsed["change_pct"],
                        volume=parsed["volume"],
                        amount=parsed["amount"],
                    )
                offset += DS_STK_RECORD_SIZE

            self.record_success()
            return None  # 未找到该股票
        except (IOError, OSError) as e:
            self.record_failure()
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量获取行情（遍历文件，过滤匹配）"""
        code_set = set(codes)
        results = []

        file_path = self._find_ds_stk_path()
        if not file_path:
            self.record_failure()
            return results

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            offset = DS_STK_HEADER_SIZE
            while offset + DS_STK_RECORD_SIZE <= len(data):
                record = data[offset : offset + DS_STK_RECORD_SIZE]
                parsed = self._parse_ds_stk_record(record)
                if parsed and parsed["code"] in code_set:
                    results.append(
                        QuoteData(
                            code=parsed["code"],
                            name=parsed["name"],
                            price=parsed["price"],
                            open_price=parsed["open"],
                            high_price=parsed["high"],
                            low_price=parsed["low"],
                            pre_close=parsed["pre_close"],
                            change=parsed["change"],
                            change_pct=parsed["change_pct"],
                            volume=parsed["volume"],
                            amount=parsed["amount"],
                        )
                    )
                    code_set.discard(parsed["code"])
                    if not code_set:
                        break
                offset += DS_STK_RECORD_SIZE

            self.record_success()
        except (IOError, OSError):
            self.record_failure()

        return results

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """
        从 .day 文件读取日线数据。
        文件路径格式：vipdoc/{sh|sz}/lday/{code}.day
        """
        # 判断市场
        market_prefix = "sh" if code.startswith("6") else "sz"
        # 通达信 .day 文件名格式为 {market_prefix}{code}.day（如 sh000001.day）
        day_file = os.path.join(
            self._data_dir, "vipdoc", market_prefix, "lday", f"{market_prefix}{code}.day"
        )

        if not os.path.isfile(day_file):
            self.record_failure()
            return []

        results = []
        try:
            with open(day_file, "rb") as f:
                data = f.read()

            # 每记录32字节：4字节日期 + 4字节开盘 + 4字节最高 + 4字节最低 + 4字节收盘
            # + 4字节成交额 + 4字节成交量 + 4字节保留
            record_count = len(data) // DAY_RECORD_SIZE
            read_count = min(count, record_count)
            start_idx = record_count - read_count

            for i in range(start_idx, record_count):
                offset = i * DAY_RECORD_SIZE
                record = data[offset : offset + DAY_RECORD_SIZE]
                if len(record) < DAY_RECORD_SIZE:
                    break

                try:
                    date_int = struct.unpack("<i", record[0:4])[0]
                    year = date_int // 10000
                    month = (date_int % 10000) // 100
                    day = date_int % 100
                    trade_date = date(year, month, day)

                    open_price = struct.unpack("<i", record[4:8])[0] / 100.0
                    high_price = struct.unpack("<i", record[8:12])[0] / 100.0
                    low_price = struct.unpack("<i", record[12:16])[0] / 100.0
                    close_price = struct.unpack("<i", record[16:20])[0] / 100.0
                    # 成交额和成交量也是整型
                    amount = struct.unpack("<i", record[20:24])[0] / 10000.0  # 万元
                    volume = struct.unpack("<i", record[24:28])[0]

                    results.append(
                        KLineData(
                            code=code,
                            trade_date=datetime.combine(trade_date, datetime.min.time()),
                            open_price=open_price,
                            close_price=close_price,
                            high_price=high_price,
                            low_price=low_price,
                            volume=volume,
                            amount=amount,
                        )
                    )
                except (struct.error, ValueError):
                    continue

            self.record_success()
        except (IOError, OSError):
            self.record_failure()

        return results

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """搜索股票（遍历 ds_stk.dat 的股票名称）"""
        results = []
        file_path = self._find_ds_stk_path()
        if not file_path:
            return results

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            keyword_lower = keyword.lower()
            offset = DS_STK_HEADER_SIZE
            while offset + DS_STK_RECORD_SIZE <= len(data):
                record = data[offset : offset + DS_STK_RECORD_SIZE]
                parsed = self._parse_ds_stk_record(record)
                if parsed:
                    name_lower = parsed["name"].lower()
                    if keyword_lower in name_lower or keyword in parsed["code"]:
                        results.append(
                            {"code": parsed["code"], "name": parsed["name"]}
                        )
                offset += DS_STK_RECORD_SIZE

            self.record_success()
        except (IOError, OSError):
            self.record_failure()

        return results[:20]  # 最多返回20条
