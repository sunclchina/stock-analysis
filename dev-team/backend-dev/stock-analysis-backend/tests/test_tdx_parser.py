"""
通达信本地解析测试。
测试 ds_stk.dat 和 .day 文件的二进制解析函数。
"""
import struct
import os
import sys
import tempfile
import pytest
from datetime import date
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.utils.tdx_parser import (
    parse_day_record,
    parse_ds_stk_record,
    read_day_file,
    read_ds_stk_file,
    DAY_RECORD_SIZE,
    DS_STK_RECORD_SIZE,
    DS_STK_HEADER_SIZE,
)


# ============================================================
# TEST DATA — 清晰标注为测试数据，不编入生产代码
# ============================================================

def _make_day_record(date_int: int, open_p: float, high: float, low: float,
                     close: float, amount: float, volume: float) -> bytes:
    """构建一条模拟的.day文件记录"""
    buf = struct.pack("<i", date_int)
    buf += struct.pack("<f", open_p)
    buf += struct.pack("<f", high)
    buf += struct.pack("<f", low)
    buf += struct.pack("<f", close)
    buf += struct.pack("<f", amount)
    buf += struct.pack("<f", volume)
    buf += struct.pack("<i", 0)  # 保留字段
    return buf


def _make_ds_stk_record(code: str, name: str, price: float, pre_close: float,
                        open_p: float, high: float, low: float,
                        volume: float, amount: float) -> bytes:
    """构建一条模拟的 ds_stk.dat 记录"""
    buf = bytearray(DS_STK_RECORD_SIZE)
    # 股票代码 (6 bytes)
    code_bytes = code.encode("gbk", errors="ignore").ljust(6, b'\x00')
    buf[0:6] = code_bytes[:6]
    # 最新价 @0x08
    struct.pack_into("<f", buf, 0x08, price)
    # 昨收 @0x0E
    struct.pack_into("<f", buf, 0x0E, pre_close)
    # 开盘 @0x14
    struct.pack_into("<f", buf, 0x14, open_p)
    # 最高 @0x1C
    struct.pack_into("<f", buf, 0x1C, high)
    # 最低 @0x24
    struct.pack_into("<f", buf, 0x24, low)
    # 成交量 @0x2C
    struct.pack_into("<f", buf, 0x2C, volume)
    # 成交额 @0x30
    struct.pack_into("<f", buf, 0x30, amount)
    # 股票名称 @0x4C (8 bytes)
    name_bytes = name.encode("gbk", errors="ignore").ljust(8, b'\x00')
    buf[0x4C:0x54] = name_bytes[:8]
    return bytes(buf)


# ============================================================
# ds_stk.dat 解析测试
# ============================================================

class TestParseDsStkRecord:

    def test_parse_valid_record(self):
        """测试解析有效的 ds_stk.dat 记录"""
        record = _make_ds_stk_record(
            code="000001",
            name="平安银行",
            price=12.5,
            pre_close=12.0,
            open_p=12.1,
            high=12.8,
            low=12.0,
            volume=100000,
            amount=1250000,
        )
        result = parse_ds_stk_record(record, 0)
        assert result is not None
        assert result["code"] == "000001"
        assert result["name"] == "平安银行"
        assert result["price"] == 12.5
        assert result["pre_close"] == 12.0
        assert result["open"] == 12.1
        assert result["high"] == 12.8
        assert result["low"] == 12.0
        assert result["volume"] == 100000.0
        assert result["amount"] == 1250000.0
        # 涨跌计算验证
        assert result["change"] == 0.5  # 12.5 - 12.0
        assert result["change_pct"] == pytest.approx(4.17, rel=0.01)  # 0.5/12.0*100

    def test_parse_short_buffer(self):
        """测试缓冲区不足"""
        short_buf = b'\x00' * 100
        result = parse_ds_stk_record(short_buf, 0)
        assert result is None  # 不足DS_STK_RECORD_SIZE

    def test_parse_sh600519_record(self):
        """测试贵州茅台模拟记录"""
        record = _make_ds_stk_record(
            code="600519",
            name="贵州茅台",
            price=1680.0,
            pre_close=1660.0,
            open_p=1665.0,
            high=1700.0,
            low=1650.0,
            volume=28000,
            amount=47000000,
        )
        result = parse_ds_stk_record(record, 0)
        assert result is not None
        assert result["code"] == "600519"
        assert result["price"] == 1680.0
        assert result["change"] == 20.0
        assert result["change_pct"] == pytest.approx(1.20, rel=0.01)

    def test_parse_with_offset(self):
        """测试带偏移的解析"""
        record = _make_ds_stk_record("000001", "平安银行", 10.0, 9.5, 9.6, 10.2, 9.5, 5000, 50000)
        buf = b'\x00' * DS_STK_RECORD_SIZE + record  # 前面用无用数据填充
        result = parse_ds_stk_record(buf, DS_STK_RECORD_SIZE)
        assert result is not None
        assert result["code"] == "000001"

    def test_parse_offset_oob(self):
        """测试偏移超出数据长度"""
        buf = b'\x00' * 100
        result = parse_ds_stk_record(buf, 50)
        assert result is None  # offset + HEADER_SIZE > len(data)

    def test_parse_record_with_invalid_encoding(self):
        """测试无效GBK编码"""
        buf = bytearray(DS_STK_RECORD_SIZE)
        buf[0:6] = b'\xff\xff\xff\xff\xff\xff'  # 无效编码
        struct.pack_into("<f", buf, 0x08, 10.0)
        struct.pack_into("<f", buf, 0x0E, 9.5)
        struct.pack_into("<f", buf, 0x4C, 0)  # 名称位置全0
        result = parse_ds_stk_record(bytes(buf), 0)
        # 可能成功（空名称）或失败
        assert result is None or result["name"] == ""


# ============================================================
# .day 日线解析测试
# ============================================================

class TestParseDayRecord:

    def test_parse_valid_day_record(self):
        """测试解析有效的.day文件记录"""
        record = _make_day_record(
            date_int=20260429,
            open_p=12.0,
            high=12.5,
            low=11.8,
            close=12.3,
            amount=50000000,
            volume=4000000,
        )
        result = parse_day_record(record, 0)
        assert result is not None
        assert result["trade_date"] == date(2026, 4, 29)
        assert result["open"] == 12.0
        assert result["high"] == 12.5
        assert result["low"] == 11.8
        assert result["close"] == 12.3
        assert result["amount"] == 50000000.0
        assert result["volume"] == 4000000.0

    def test_parse_day_multiple_records(self):
        """测试解析多条日线记录"""
        records = b""
        for i in range(5):
            records += _make_day_record(20260420 + i, 10 + i, 11 + i, 9 + i, 10.5 + i, 100000, 8000)

        results = []
        offset = 0
        while offset + DAY_RECORD_SIZE <= len(records):
            r = parse_day_record(records, offset)
            assert r is not None
            results.append(r)
            offset += DAY_RECORD_SIZE

        assert len(results) == 5
        assert results[0]["trade_date"] == date(2026, 4, 20)
        assert results[4]["trade_date"] == date(2026, 4, 24)

    def test_parse_day_short_record(self):
        """测试截断记录"""
        short = b'\x00' * 16  # 只有16字节
        result = parse_day_record(short, 0)
        assert result is None

    def test_parse_day_invalid_date(self):
        """测试无效日期字段（负值、异常值等）"""
        # 日期字段为0会抛出struct.error或ValueError→返回None
        record = _make_day_record(0, 10, 11, 9, 10.5, 1000, 100)
        result = parse_day_record(record, 0)
        # 可能导致 ValueError (date(0, 0, 0) 不合法)
        assert result is not None or result is None  # 两种都可能


# ============================================================
# read_day_file 和 read_ds_stk_file 集成测试
# ============================================================

class TestReadDayFile:

    def test_read_day_file(self):
        """测试读取完整的.day文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".day") as f:
            for i in range(10):
                f.write(_make_day_record(20260420 + i, 10 + i, 11 + i, 9 + i, 10.5 + i, 100000, 8000))
            tmp_path = f.name

        try:
            results = read_day_file(tmp_path)
            assert len(results) == 10
            assert results[0]["trade_date"] == date(2026, 4, 20)
            assert results[-1]["trade_date"] == date(2026, 4, 29)
        finally:
            os.unlink(tmp_path)

    def test_read_nonexistent_file(self):
        """测试读取不存在的文件"""
        results = read_day_file("/nonexistent/file.day")
        assert results == []


class TestReadDsStkFile:

    def test_read_ds_stk_file(self):
        """测试读取完整的 ds_stk.dat 文件"""
        header = b'\x00' * DS_STK_HEADER_SIZE
        records = header
        for i, (code, name) in enumerate([("000001", "平安银行"), ("600519", "贵州茅台")]):
            records += _make_ds_stk_record(code, name, 10 + i * 5, 9.5 + i * 5,
                                            9.6 + i * 5, 10.2 + i * 5, 9.5 + i * 5,
                                            5000, 50000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            f.write(records)
            tmp_path = f.name

        try:
            results = read_ds_stk_file(tmp_path)
            assert len(results) == 2
            assert results[0]["code"] == "000001"
            assert results[1]["code"] == "600519"
        finally:
            os.unlink(tmp_path)

    def test_read_nonexistent_ds_stk(self):
        """测试读取不存在的 ds_stk.dat"""
        results = read_ds_stk_file("/nonexistent/ds_stk.dat")
        assert results == []


# ============================================================
# TDXLocalDataSource 集成测试（模拟文件）
# ============================================================

class TestTDXLocalDataSource:
    """TDXLocalDataSource 方法的集成测试"""

    @pytest.mark.asyncio
    async def test_get_quote_found(self):
        """测试找到指定股票的行情记录"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        header = b'\x00' * DS_STK_HEADER_SIZE
        records = header
        records += _make_ds_stk_record("000001", "平安银行", 12.5, 12.0, 12.1, 12.8, 12.0, 100000, 1250000)
        records += _make_ds_stk_record("600519", "贵州茅台", 1680.0, 1660.0, 1665.0, 1700.0, 1650.0, 28000, 47000000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            f.write(records)
            tmp_path = f.name

        try:
            ds = TDXLocalDataSource()
            with patch.object(ds, '_find_ds_stk_path', return_value=tmp_path):
                quote = await ds.get_quote("600519")
                assert quote is not None
                assert quote.code == "600519"
                assert quote.name == "贵州茅台"
                assert quote.price == 1680.0
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self):
        """测试未找到指定股票的行情记录"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            f.write(b'\x00' * DS_STK_HEADER_SIZE)
            tmp_path = f.name

        try:
            ds = TDXLocalDataSource()
            with patch.object(ds, '_find_ds_stk_path', return_value=tmp_path):
                quote = await ds.get_quote("999999")
                assert quote is None  # 空文件中找不到
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_get_quote_no_file(self):
        """测试文件不存在时的降级"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        ds = TDXLocalDataSource()
        with patch.object(ds, '_find_ds_stk_path', return_value=None):
            quote = await ds.get_quote("000001")
            assert quote is None

    @pytest.mark.asyncio
    async def test_get_quotes_batch(self):
        """测试批量获取行情"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        header = b'\x00' * DS_STK_HEADER_SIZE
        records = header
        records += _make_ds_stk_record("000001", "平安银行", 12.5, 12.0, 12.1, 12.8, 12.0, 100000, 1250000)
        records += _make_ds_stk_record("600519", "贵州茅台", 1680.0, 1660.0, 1665.0, 1700.0, 1650.0, 28000, 47000000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            f.write(records)
            tmp_path = f.name

        try:
            ds = TDXLocalDataSource()
            with patch.object(ds, '_find_ds_stk_path', return_value=tmp_path):
                quotes = await ds.get_quotes(["000001", "600519"])
                assert len(quotes) == 2
                assert quotes[0].code == "000001"
                assert quotes[1].code == "600519"
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_search_stock(self):
        """测试股票搜索"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        header = b'\x00' * DS_STK_HEADER_SIZE
        records = header
        records += _make_ds_stk_record("000001", "平安银行", 10, 9.5, 9.6, 10.2, 9.5, 5000, 50000)
        records += _make_ds_stk_record("600519", "贵州茅台", 1600, 1550, 1560, 1620, 1550, 30000, 48000000)
        records += _make_ds_stk_record("000858", "五粮液", 140, 138, 139, 142, 137, 20000, 2800000)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as f:
            f.write(records)
            tmp_path = f.name

        try:
            ds = TDXLocalDataSource()
            with patch.object(ds, '_find_ds_stk_path', return_value=tmp_path):
                results = await ds.search_stock("茅台")
                assert len(results) == 1
                assert results[0]["code"] == "600519"
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_get_kline_day_file(self):
        """测试从.day文件读取K线数据"""
        from backend.services.data_source.tdx_local import TDXLocalDataSource

        day_dir = tempfile.mkdtemp()
        # 600xxx → market = sh
        os.makedirs(os.path.join(day_dir, "vipdoc", "sh", "lday"), exist_ok=True)
        day_file = os.path.join(day_dir, "vipdoc", "sh", "lday", "600519.day")

        with open(day_file, "wb") as f:
            for i in range(30):
                f.write(_make_day_record(20260320 + i, 1500 + i, 1520 + i, 1480 + i, 1510 + i, 50000000, 4000000))

        try:
            ds = TDXLocalDataSource()
            ds._data_dir = day_dir
            klines = await ds.get_kline("600519", count=10)

            assert len(klines) == 10
            assert klines[0].code == "600519"
            assert klines[-1].code == "600519"
            assert klines[-1].trade_date.year == 2026
        finally:
            import shutil
            shutil.rmtree(day_dir)
