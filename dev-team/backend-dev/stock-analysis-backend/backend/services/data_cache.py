"""
数据持久缓存层 — 本地 SQLite 缓存日线K线和分时数据。

设计原则：
  1. 一次拉取，本地落地，后续请求读缓存
  2. 增量更新：只拉取缺失数据，不重复请求已有数据
  3. 分时数据按日过期（仅缓存当日），K线数据按需保留

用法：
  from backend.services.data_cache import kline_cache, timeshare_cache

  # K线：读取缓存，缺失部分自动从回调拉取
  klines = await kline_cache.get_or_fetch("600519", fetch_callback)

  # 分时：读取缓存，不存在则从回调拉取
  ts = await timeshare_cache.get_or_fetch("600519", fetch_callback)
"""

import logging
import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Callable, Awaitable

from sqlalchemy import text
from backend.config.database import async_session_factory, engine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 建表
# ─────────────────────────────────────────────

INIT_SQL = """
CREATE TABLE IF NOT EXISTS kline_cache (
    code         VARCHAR(10)  NOT NULL,
    trade_date   DATE         NOT NULL,
    open         REAL,
    close       REAL,
    high        REAL,
    low         REAL,
    volume      REAL,
    amount      REAL,
    cached_at    DATETIME DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (code, trade_date)
);

CREATE TABLE IF NOT EXISTS timeshare_cache (
    code       VARCHAR(10) NOT NULL,
    trade_date  DATE        NOT NULL,
    time_point  TEXT        NOT NULL,
    price      REAL,
    avg_price  REAL,
    volume     REAL,
    amount     REAL,
    cached_at   DATETIME DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (code, trade_date, time_point)
);

CREATE INDEX IF NOT EXISTS idx_kline_code_date ON kline_cache(code, trade_date);
CREATE INDEX IF NOT EXISTS idx_timeshare_code_date ON timeshare_cache(code, trade_date);
"""


async def init_cache_tables():
    """初始化缓存表（幂等）"""
    try:
        async with engine.begin() as conn:
            for stmt in INIT_SQL.split(";"):
                s = stmt.strip()
                if s:
                    await conn.execute(text(s))
        logger.info("数据缓存表初始化完成")
    except Exception as e:
        logger.warning(f"数据缓存表初始化失败: {e}")


# ─────────────────────────────────────────────
# K线缓存
# ─────────────────────────────────────────────

class KlineCache:
    """日线K线持久缓存，支持增量补采"""

    async def get_or_fetch(
        self,
        code: str,
        fetcher: Callable[[str, date], Awaitable[List[Dict[str, Any]]]],
        max_days: int = 120,
    ) -> List[Dict[str, Any]]:
        """
        读取缓存 + 增量补采。

        fetcher(code, since_date) → kline_dict_list
          回调函数，只拉取 since_date 之后的数据（不含 since_date）
          返回 [{trade_date, open, close, high, low, volume, amount}, ...]
        """
        clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

        # 1. 查缓存中最新日期
        latest = await self._latest_date(clean_code)
        today = date.today()

        # 2. 判断是否需要增量补采
        need_fetch = False
        fetch_since = None
        if latest is None:
            need_fetch = True
            fetch_since = None  # 全量
        elif latest < today:
            # 有缓存但不是最新的 → 增量
            need_fetch = True
            fetch_since = latest
            logger.debug(f"K线增量补采 {clean_code} 自 {fetch_since}")

        # 3. 从 API 拉取缺失数据
        if need_fetch:
            try:
                new_klines = await fetcher(clean_code, fetch_since)
                if new_klines:
                    await self._bulk_save(clean_code, new_klines)
                    logger.info(f"K线缓存更新 {clean_code}: +{len(new_klines)} 条")
            except Exception as e:
                logger.warning(f"K线增量补采失败 {clean_code}: {e}")

        # 4. 读取全部缓存返回
        return await self._get_all(clean_code, max_days)

    async def _latest_date(self, code: str) -> Optional[date]:
        try:
            async with async_session_factory() as db:
                row = await db.execute(
                    text("SELECT MAX(trade_date) FROM kline_cache WHERE code = :code"),
                    {"code": code},
                )
                result = row.scalar()
                if result:
                    if isinstance(result, str):
                        return date.fromisoformat(result)
                    return result
        except Exception as e:
            logger.debug(f"K线缓存查询最新日期失败 {code}: {e}")
        return None

    async def _bulk_save(self, code: str, klines: List[Dict[str, Any]]):
        """批量写入K线缓存（UPSERT）"""
        try:
            async with async_session_factory() as db:
                for k in klines:
                    td = k.get("trade_date")
                    if isinstance(td, datetime):
                        td = td.date()
                    elif isinstance(td, str):
                        td_s = td[:10]
                        td = date.fromisoformat(td_s)
                    await db.execute(
                        text("""
                            INSERT OR REPLACE INTO kline_cache
                            (code, trade_date, open, close, high, low, volume, amount)
                            VALUES (:code, :trade_date, :open, :close, :high, :low, :volume, :amount)
                        """),
                        {
                            "code": code,
                            "trade_date": td,
                            "open": k.get("open"),
                            "close": k.get("close"),
                            "high": k.get("high"),
                            "low": k.get("low"),
                            "volume": k.get("volume"),
                            "amount": k.get("amount"),
                        },
                    )
                await db.commit()
        except Exception as e:
            logger.warning(f"K线缓存批量写入失败 {code}: {e}")

    async def _get_all(self, code: str, max_days: int) -> List[Dict[str, Any]]:
        """读取全部缓存K线（按日期升序，限制最大条数）"""
        try:
            async with async_session_factory() as db:
                rows = await db.execute(
                    text("""
                        SELECT trade_date, open, close, high, low, volume, amount
                        FROM kline_cache
                        WHERE code = :code
                        ORDER BY trade_date DESC
                        LIMIT :limit
                    """),
                    {"code": code, "limit": max_days},
                )
                result = []
                for row in rows.fetchall():
                    result.append({
                        "trade_date": str(row[0]) if hasattr(row[0], 'isoformat') else row[0],
                        "open": row[1],
                        "close": row[2],
                        "high": row[3],
                        "low": row[4],
                        "volume": row[5],
                        "amount": row[6],
                    })
                # 升序返回
                result.reverse()
                return result
        except Exception as e:
            logger.warning(f"K线缓存读取失败 {code}: {e}")
            return []

    async def invalidate(self, code: str):
        """主动失效某只股票的缓存"""
        try:
            async with async_session_factory() as db:
                await db.execute(
                    text("DELETE FROM kline_cache WHERE code = :code"),
                    {"code": code},
                )
                await db.commit()
                logger.info(f"K线缓存已清除 {code}")
        except Exception as e:
            logger.warning(f"K线缓存清除失败 {code}: {e}")


# ─────────────────────────────────────────────
# 分时数据缓存
# ─────────────────────────────────────────────

class TimeshareCache:
    """当日分时数据缓存（按日过期）"""

    async def get_or_fetch(
        self,
        code: str,
        fetcher: Callable[[str], Awaitable[List[Dict[str, Any]]]],
    ) -> List[Dict[str, Any]]:
        """
        读缓存 / 拉取当日分时数据。

        fetcher(code) → timeshare_list
          回调函数，返回 [{time, price, avg_price, volume, amount}, ...]
        """
        clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        today = date.today()

        # 1. 检查当日是否已有缓存
        cached = await self._get_today(clean_code, today)
        if cached is not None:
            return cached

        # 2. 拉取
        try:
            items = await fetcher(clean_code)
            if items:
                await self._save_today(clean_code, today, items)
                logger.info(f"分时缓存更新 {clean_code}: {len(items)} 条")
            return items
        except Exception as e:
            logger.warning(f"分时数据拉取失败 {clean_code}: {e}")
            return []

    async def _get_today(self, code: str, trade_date: date) -> Optional[List[Dict[str, Any]]]:
        try:
            async with async_session_factory() as db:
                rows = await db.execute(
                    text("""
                        SELECT time_point, price, avg_price, volume, amount
                        FROM timeshare_cache
                        WHERE code = :code AND trade_date = :trade_date
                        ORDER BY time_point
                    """),
                    {"code": code, "trade_date": trade_date},
                )
                results = rows.fetchall()
                if results:
                    return [
                        {
                            "time": r[0],
                            "price": r[1],
                            "avg_price": r[2],
                            "volume": r[3],
                            "amount": r[4],
                        }
                        for r in results
                    ]
        except Exception as e:
            logger.debug(f"分时缓存读取失败 {code}: {e}")
        return None

    async def _save_today(self, code: str, trade_date: date, items: List[Dict[str, Any]]):
        """批量写入当日分时缓存"""
        try:
            async with async_session_factory() as db:
                # 先清掉旧数据（防重复）
                await db.execute(
                    text("DELETE FROM timeshare_cache WHERE code = :code AND trade_date = :trade_date"),
                    {"code": code, "trade_date": trade_date},
                )
                for item in items:
                    await db.execute(
                        text("""
                            INSERT INTO timeshare_cache
                            (code, trade_date, time_point, price, avg_price, volume, amount)
                            VALUES (:code, :trade_date, :time_point, :price, :avg_price, :volume, :amount)
                        """),
                        {
                            "code": code,
                            "trade_date": trade_date,
                            "time_point": item.get("time", ""),
                            "price": item.get("price"),
                            "avg_price": item.get("avg_price"),
                            "volume": item.get("volume"),
                            "amount": item.get("amount"),
                        },
                    )
                await db.commit()
        except Exception as e:
            logger.warning(f"分时缓存写入失败 {code}: {e}")


# ─────────────────────────────────────────────
# 全局单例
# ─────────────────────────────────────────────

kline_cache = KlineCache()
timeshare_cache = TimeshareCache()
