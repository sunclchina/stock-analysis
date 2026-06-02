"""
AkShare数据源（免费备用数据源）。
通过 AkShare 库获取 A 股实时行情、板块数据、北向资金等。

AkShare（https://github.com/akfamily/akshare）是基于东方财富等多个数据源的
Python 开源财经数据接口库，免费且数据维度丰富。

主要接口：
- stock_zh_a_spot()        实时行情（含换手率、振幅、量比等）
- stock_board_industry_spot_em() 板块行情
- stock_hsgt_north_net_flow_in_em() 北向资金

重要：所有 self._ak.xxx() 同步调用必须通过 _call_ak() 在线程池中执行，
避免阻塞 Uvicorn async 事件循环。
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

from backend.services.data_source.base import BaseDataSource, QuoteData, KLineData

logger = logging.getLogger(__name__)

# AKShare 专用线程池（隔离所有同步调用，避免阻塞 async 事件循环）
_AKSHARE_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="akshare")


class AkShareDataSource(BaseDataSource):
    """AkShare 数据源"""

    def __init__(self):
        super().__init__(name="akshare")
        self._imported = False

    def _ensure_import(self):
        """延迟导入 akshare（避免启动时加载过慢）"""
        if not self._imported:
            import akshare as ak
            self._ak = ak
            self._imported = True

    async def _call_ak(self, func, *args, **kwargs):
        """
        在线程池中执行 AKShare 同步函数，返回结果。
        所有 self._ak.xxx() 调用必须通过此方法，避免阻塞事件循环。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_AKSHARE_POOL, lambda: func(*args, **kwargs))

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        """获取单只股票实时行情"""
        try:
            self._ensure_import()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            df = await self._call_ak(self._ak.stock_zh_a_spot)
            if df is None or df.empty:
                self.record_failure()
                return None
            row = df[df['代码'] == clean]
            if row.empty:
                self.record_failure()
                return None
            result = self._row_to_quote(row.iloc[0])
            if result is not None:
                self.record_success()
            return result
        except Exception as e:
            logger.warning(f"AkShare get_quote({code}) failed: {e}")
            self.record_failure()
            return None

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        """批量获取实时行情（一次获取全市场数据）"""
        try:
            self._ensure_import()
            clean_codes = set()
            for c in codes:
                clean = c.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
                clean_codes.add(clean)

            df = await self._call_ak(self._ak.stock_zh_a_spot)
            if df is None or df.empty:
                self.record_failure()
                return []

            results = []
            matched = df[df['代码'].isin(clean_codes)]
            for _, row in matched.iterrows():
                q = self._row_to_quote(row)
                if q:
                    results.append(q)

            self.record_success()
            return results
        except Exception as e:
            logger.warning(f"AkShare get_quotes failed: {e}")
            self.record_failure()
            return []

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """获取日K线数据"""
        try:
            self._ensure_import()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            market = "sh" if clean.startswith(("6", "9")) else "sz"
            df = await self._call_ak(
                self._ak.stock_zh_a_hist, symbol=clean, period="daily",
                start_date="20000101", adjust="qfq"
            )
            if df is None or df.empty:
                self.record_failure()
                return []
            df = df.tail(count)
            results = []
            for _, row in df.iterrows():
                try:
                    dt = datetime.strptime(str(row['日期']), "%Y-%m-%d")
                except ValueError:
                    continue
                results.append(KLineData(
                    code=clean, trade_date=dt,
                    open_price=float(row['开盘']), close_price=float(row['收盘']),
                    high_price=float(row['最高']), low_price=float(row['最低']),
                    volume=float(row['成交量']), amount=float(row['成交额']),
                ))
            self.record_success()
            return results
        except Exception as e:
            logger.warning(f"AkShare get_kline({code}) failed: {e}")
            self.record_failure()
            return []

    async def search_stock(self, keyword: str) -> List[Dict[str, str]]:
        """搜索股票"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_zh_a_spot)
            if df is None or df.empty:
                return []
            matched = df[df['名称'].str.contains(keyword, na=False) |
                         df['代码'].str.contains(keyword, na=False)]
            results = []
            for _, row in matched.head(20).iterrows():
                results.append({"code": str(row['代码']), "name": str(row['名称'])})
            return results
        except Exception as e:
            logger.warning(f"AkShare search failed: {e}")
            return []

    # ── 扩展接口：用于盘前提示 ──

    async def get_sector_performance(self) -> Dict[str, Any]:
        """获取板块涨跌排行"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_board_industry_spot_em)
            if df is None or df.empty:
                return {"leaders": [], "laggards": []}
            leaders, laggards = [], []
            for _, row in df.head(8).iterrows():
                name = str(row.get('板块名称', ''))
                chg = row.get('涨跌幅')
                if name and chg is not None:
                    entry = {"name": name, "chg": round(float(chg), 2)}
                    (leaders if float(chg) > 0 else laggards).append(entry)
            self.record_success()
            return {"leaders": leaders[:5], "laggards": laggards[:3]}
        except Exception as e:
            logger.warning(f"AkShare sector perf failed: {e}")
            return {"leaders": [], "laggards": []}

    async def get_northbound_flow(self) -> Dict[str, str]:
        """获取北向资金（当日+近5日累计）"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_hsgt_north_net_flow_in_em, symbol="北上")
            if df is None or df.empty:
                return {"today": "", "cum5": ""}
            result = {"today": "", "cum5": ""}
            latest = df.iloc[-1]
            total = float(latest.get('成交净买入', 0))
            sh = float(latest.get('沪股通', 0))
            sz = float(latest.get('深股通', 0))
            d = "净流入" if total > 0 else "净流出"
            result["today"] = f"北向资金{d}{abs(total):.0f}亿（沪股通{abs(sh):.0f}亿，深股通{abs(sz):.0f}亿）"
            recent = df.tail(5)
            total5 = recent['成交净买入'].sum()
            d5 = "净流入" if total5 > 0 else "净流出"
            result["cum5"] = f"近5日累计{d5}{abs(total5):.0f}亿"
            self.record_success()
            return result
        except Exception as e:
            logger.warning(f"AkShare northbound flow failed: {e}")
            return {"today": "", "cum5": ""}

    async def get_concept_sectors(self) -> List[Dict[str, Any]]:
        """获取概念板块涨跌排行（东方财富分类）"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_board_concept_spot_em)
            if df is None or df.empty:
                return []
            results = []
            for _, row in df.iterrows():
                results.append({
                    "name": str(row.get("板块名称", "")),
                    "code": str(row.get("板块代码", "")),
                    "price": round(float(row.get("最新价", 0)), 2),
                    "change_pct": round(float(row.get("涨跌幅", 0)), 2),
                    "change_amount": round(float(row.get("涨跌额", 0)), 2),
                    "volume": round(float(row.get("成交量", 0)), 2),
                    "amount": round(float(row.get("成交额", 0)), 2),
                    "turnover_rate": round(float(row.get("换手率", 0)), 2),
                    "leading_stock": str(row.get("领涨股", "")),
                    "leading_stock_code": str(row.get("领涨股代码", "")),
                    "leading_stock_price": round(float(row.get("领涨股最新价", 0)), 2),
                    "leading_stock_change": round(float(row.get("领涨股涨跌幅", 0)), 2),
                })
            self.record_success()
            return results
        except Exception as e:
            logger.warning(f"AkShare concept sectors failed: {e}")
            return []

    async def get_industry_sectors_detailed(self) -> List[Dict[str, Any]]:
        """获取行业板块详细行情"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_board_industry_spot_em)
            if df is None or df.empty:
                return []
            results = []
            for _, row in df.iterrows():
                results.append({
                    "name": str(row.get("板块名称", "")),
                    "code": str(row.get("板块代码", "")),
                    "price": round(float(row.get("最新价", 0)), 2),
                    "change_pct": round(float(row.get("涨跌幅", 0)), 2),
                    "change_amount": round(float(row.get("涨跌额", 0)), 2),
                    "volume": round(float(row.get("成交量", 0)), 2),
                    "amount": round(float(row.get("成交额", 0)), 2),
                    "turnover_rate": round(float(row.get("换手率", 0)), 2),
                    "leading_stock": str(row.get("领涨股", "")),
                    "leading_stock_code": str(row.get("领涨股代码", "")),
                })
            self.record_success()
            return results
        except Exception as e:
            logger.warning(f"AkShare industry sectors failed: {e}")
            return []

    async def get_individual_fund_flow(self, code: str) -> Dict[str, Any]:
        """获取个股资金流（主力/超大单/大单/中单/小单）"""
        try:
            self._ensure_import()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            market = "sh" if clean.startswith(("6", "9")) else "sz"
            df = await self._call_ak(self._ak.stock_individual_fund_flow, clean, market)
            if df is None or df.empty:
                return {}
            latest = df.iloc[-1]
            self.record_success()
            return {
                "code": clean,
                "date": str(latest.get("日期", "")),
                "main_net": round(float(latest.get("主力净流入-净额", 0)), 2),
                "main_net_pct": round(float(latest.get("主力净流入-净占比", 0)), 2),
                "super_large_net": round(float(latest.get("超大单净流入-净额", 0)), 2),
                "super_large_pct": round(float(latest.get("超大单净流入-净占比", 0)), 2),
                "large_net": round(float(latest.get("大单净流入-净额", 0)), 2),
                "large_pct": round(float(latest.get("大单净流入-净占比", 0)), 2),
                "medium_net": round(float(latest.get("中单净流入-净额", 0)), 2),
                "medium_pct": round(float(latest.get("中单净流入-净占比", 0)), 2),
                "small_net": round(float(latest.get("小单净流入-净额", 0)), 2),
                "small_pct": round(float(latest.get("小单净流入-净占比", 0)), 2),
            }
        except Exception as e:
            logger.warning(f"AkShare fund flow({code}) failed: {e}")
            return {}

    async def get_individual_info(self, code: str) -> Dict[str, Any]:
        """获取个股基本信息（交易所、行业、市盈率、总市值等）"""
        try:
            self._ensure_import()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            df = await self._call_ak(self._ak.stock_individual_info_em, symbol=clean)
            if df is None or df.empty:
                return {}
            info = {}
            for _, row in df.iterrows():
                item = str(row.get("item", ""))
                val = str(row.get("value", ""))
                info[item] = val
            self.record_success()
            return {
                "code": clean,
                "name": info.get("股票简称", ""),
                "market": info.get("上市板块", ""),
                "industry": info.get("行业", ""),
                "total_market_cap": info.get("总市值", ""),
                "circulating_market_cap": info.get("流通市值", ""),
                "pe": info.get("市盈率-动态", ""),
                "pb": info.get("市净率", ""),
            }
        except Exception as e:
            logger.warning(f"AkShare individual info({code}) failed: {e}")
            return {}

    async def get_limit_up_pool(self) -> List[Dict[str, Any]]:
        """获取涨停股池（带磁盘缓存，非交易时段返回最近交易日数据）"""
        cache_file = "data/a_share_cache/limit_up_cache.json"

        try:
            self._ensure_import()
            today_str = datetime.now().strftime("%Y%m%d")
            for fn, date_arg in [
                (self._ak.stock_zt_pool_em, today_str),
                (self._ak.stock_zt_pool_previous_em, today_str),
                (self._ak.stock_zt_pool_strong_em, today_str),
            ]:
                try:
                    df = await self._call_ak(fn, date=date_arg)
                    if df is not None and not df.empty:
                        results = []
                        for _, row in df.iterrows():
                            results.append({
                                "code": str(row.get("代码", "")),
                                "name": str(row.get("名称", "")),
                                "price": round(float(row.get("最新价", 0)), 2),
                                "change_pct": round(float(row.get("涨跌幅", 0)), 2),
                                "turnover_rate": round(float(row.get("换手率", 0)), 2),
                                "amount": round(float(row.get("成交额", 0)), 2),
                                "amplitude": round(float(row.get("振幅", 0)), 2),
                                "limit_up_reason": str(row.get("封板原因", "")),
                                "limit_up_times": str(row.get("连板数", "")),
                                "limit_up_type": str(row.get("涨停类型", "")),
                            })
                        if results:
                            try:
                                import json
                                with open(cache_file, "w", encoding="utf-8") as f:
                                    json.dump({"stocks": results, "date": datetime.now().strftime("%Y-%m-%d")}, f, ensure_ascii=False)
                            except Exception:
                                pass
                        self.record_success()
                        return results
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"AkShare limit up pool failed: {e}")

        try:
            import json
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("stocks"):
                logger.info(f"涨停股池: 使用缓存数据 ({cached.get('date','?')})")
                return cached["stocks"]
        except Exception:
            pass
        return []

    async def get_limit_up_down(self) -> str:
        """获取涨停/跌停家数"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_zh_a_spot)
            if df is None or df.empty:
                return ""
            up_count = len(df[df['涨跌幅'] >= 9.8])
            down_count = len(df[df['涨跌幅'] <= -9.8])
            self.record_success()
            return f"涨停{up_count}家，跌停{down_count}家"
        except Exception as e:
            logger.warning(f"AkShare limit up/down failed: {e}")
            return ""

    async def get_market_turnover(self) -> str:
        """获取两市总成交额"""
        try:
            self._ensure_import()
            df = await self._call_ak(self._ak.stock_zh_a_spot)
            if df is None or df.empty:
                return ""
            total_amt = df['成交额'].sum() / 1e8
            self.record_success()
            return f"两市成交额约{total_amt:.0f}亿元"
        except Exception as e:
            logger.warning(f"AkShare turnover failed: {e}")
            return ""

    # ── 内部方法 ──

    @staticmethod
    def _row_to_quote(row) -> Optional[QuoteData]:
        """将 akshare DataFrame 行转为 QuoteData"""
        try:
            code = str(row.get('代码', ''))
            name = str(row.get('名称', ''))
            price = float(row.get('最新价', 0))
            open_price = float(row.get('今开', 0))
            high = float(row.get('最高', 0))
            low = float(row.get('最低', 0))
            pre_close = float(row.get('昨收', 0))
            change = float(row.get('涨跌额', 0))
            change_pct = float(row.get('涨跌幅', 0))
            volume = float(row.get('成交量', 0))
            amount = float(row.get('成交额', 0))
            turnover_rate = float(row.get('换手率', 0))
            amplitude = float(row.get('振幅', 0))

            return QuoteData(
                code=code, name=name,
                price=round(price, 2), open_price=round(open_price, 2),
                high_price=round(high, 2), low_price=round(low, 2),
                pre_close=round(pre_close, 2),
                change=round(change, 2), change_pct=round(change_pct, 2),
                volume=volume, amount=amount,
                turnover_rate=round(turnover_rate, 2),
                amplitude=round(amplitude, 2),
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"AkShare row parse failed: {e}")
            return None
