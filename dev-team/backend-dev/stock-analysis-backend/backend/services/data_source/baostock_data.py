"""
Baostock+ 数据源（备用数据源）。
通过 baostock 库获取免费历史日线/分钟线数据。
主要用于 K 线数据的备用来源。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
import logging

from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData

logger = logging.getLogger(__name__)


class BaostockDataSource(BaseDataSource):
    """Baostock 历史数据源"""

    def __init__(self):
        super().__init__(name="baostock")
        self._logged_in = False

    def _ensure_login(self):
        if not self._logged_in:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                self._logged_in = True
            else:
                logger.warning(f"Baostock登录失败: {lg.error_msg}")

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """Baostock 无实时行情"""
        return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """Baostock 无批量实时行情"""
        return []

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """获取日K线数据（备用）"""
        try:
            self._ensure_login()
            if not self._logged_in:
                return []

            import baostock as bs
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            # 判断市场
            prefix = "sh" if clean.startswith(("6", "9")) else "sz"

            rs = bs.query_history_k_data_plus(
                f"{prefix}.{clean}",
                "date,open,high,low,close,volume,amount",
                start_date="20000101",
                frequency="d", count=count
            )
            if rs.error_code != '0':
                return []

            results = []
            while rs.next():
                row = rs.get_row_data()
                try:
                    dt = datetime.strptime(row[0], "%Y-%m-%d")
                except ValueError:
                    continue
                results.append(KLineData(
                    code=clean, trade_date=dt,
                    open_price=float(row[1]), close_price=float(row[4]),
                    high_price=float(row[2]), low_price=float(row[3]),
                    volume=float(row[5]), amount=float(row[6]),
                ))
            return results
        except Exception as e:
            logger.warning(f"Baostock kline failed: {e}")
            return []

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """Baostock 不支持搜索"""
        return []

    def __del__(self):
        if self._logged_in:
            try:
                import baostock as bs
                bs.logout()
            except Exception:
                pass
