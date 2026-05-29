"""
通达信数据文件底层解析工具。
提供不通达信数据文件格式的底层解析函数。

支持的格式：
1. ds_stk.dat — 盘后行情缓存
2. .day — 日线文件
3. .min — 分钟线文件（待实现）
4. .lc1/.lc5 — 5/15/30/60分钟线（待实现）
"""

import struct
import os
from datetime import date, datetime
from typing import Optional, List, Dict, Any, BinaryIO, Tuple

# 常用记录长度
DAY_RECORD_SIZE = 32       # 日线每记录32字节
MINUTE_RECORD_SIZE = 32    # 分钟线每记录32字节
DS_STK_RECORD_SIZE = 306   # ds_stk.dat每记录306字节
DS_STK_HEADER_SIZE = 0x98  # ds_stk.dat文件头0x98字节


def parse_day_record(data: bytes, offset: int) -> Optional[Dict[str, Any]]:
    """
    解析.day文件的单条日线记录。
    
    格式（32字节）：
    0-3:  日期 (int, YYYYMMDD)
    4-7:  开盘价 (float)
    8-11: 最高价 (float)
    12-15: 最低价 (float)
    16-19: 收盘价 (float)
    20-23: 成交额 (float)
    24-27: 成交量 (float)
    28-31: 保留
    """
    if offset + DAY_RECORD_SIZE > len(data):
        return None

    try:
        rec = data[offset : offset + DAY_RECORD_SIZE]
        date_int = struct.unpack("<i", rec[0:4])[0]
        year = date_int // 10000
        month = (date_int % 10000) // 100
        day = date_int % 100

        return {
            "trade_date": date(year, month, day),
            "open": round(struct.unpack("<f", rec[4:8])[0], 2),
            "high": round(struct.unpack("<f", rec[8:12])[0], 2),
            "low": round(struct.unpack("<f", rec[12:16])[0], 2),
            "close": round(struct.unpack("<f", rec[16:20])[0], 2),
            "amount": round(struct.unpack("<f", rec[20:24])[0], 2),
            "volume": round(struct.unpack("<f", rec[24:28])[0], 2),
        }
    except (struct.error, ValueError):
        return None


def parse_ds_stk_record(data: bytes, offset: int) -> Optional[Dict[str, Any]]:
    """
    解析 ds_stk.dat 的行情记录。
    
    偏移说明（不同通达信版本有差异，以下是典型布局）：
    0-5:   市场代码+股票代码 (6 bytes)
    0x08:  最新价 (float)
    0x0E:  昨收 (float)
    0x14:  开盘 (float)
    0x1C:  最高 (float)
    0x24:  最低 (float)
    0x4C:  股票名称 (8 bytes GBK)
    """
    if offset + DS_STK_RECORD_SIZE > len(data):
        return None

    try:
        rec = data[offset : offset + DS_STK_RECORD_SIZE]

        code = rec[0:6].decode("gbk", errors="ignore").strip(" \x00")
        name = rec[0x4C:0x54].decode("gbk", errors="ignore").strip(" \x00")

        price = struct.unpack("<f", rec[0x08:0x0C])[0]
        pre_close = struct.unpack("<f", rec[0x0E:0x12])[0]
        open_price = struct.unpack("<f", rec[0x14:0x18])[0]
        high = struct.unpack("<f", rec[0x1C:0x20])[0]
        low = struct.unpack("<f", rec[0x24:0x28])[0]
        volume = struct.unpack("<f", rec[0x2C:0x30])[0]
        amount = struct.unpack("<f", rec[0x30:0x34])[0]

        change = price - pre_close if pre_close else 0.0
        change_pct = (change / pre_close * 100) if pre_close else 0.0

        return {
            "code": code,
            "name": name,
            "price": round(price, 2),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "pre_close": round(pre_close, 2),
            "volume": round(volume, 2),
            "amount": round(amount, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except (struct.error, UnicodeDecodeError, IndexError):
        return None


def read_day_file(filepath: str) -> List[Dict[str, Any]]:
    """读取完整的.day日线文件"""
    if not os.path.isfile(filepath):
        return []

    results = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        offset = 0
        while offset + DAY_RECORD_SIZE <= len(data):
            record = parse_day_record(data, offset)
            if record:
                results.append(record)
            offset += DAY_RECORD_SIZE
    except (IOError, OSError):
        pass

    return results


def read_ds_stk_file(filepath: str) -> List[Dict[str, Any]]:
    """读取完整的 ds_stk.dat 行情文件"""
    if not os.path.isfile(filepath):
        return []

    results = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()

        offset = DS_STK_HEADER_SIZE
        while offset + DS_STK_RECORD_SIZE <= len(data):
            record = parse_ds_stk_record(data, offset)
            if record:
                results.append(record)
            offset += DS_STK_RECORD_SIZE
    except (IOError, OSError):
        pass

    return results
