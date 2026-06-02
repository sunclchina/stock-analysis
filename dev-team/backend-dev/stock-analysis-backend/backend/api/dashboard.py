"""
M01 系统仪表盘API - 完整实现。

遵循架构方案4.1节 M01 仪表盘接口定义:
GET /api/v1/dashboard - 返回:
- 系统状态摘要(数据源连接状态、预警引擎状态)
- 大盘概览(调用 market overview)
- 预警汇总(按类型/级别统计)
- 自选/监控池快照
- 最近分析结论

依赖 M02/M03/M05/M06 模块数据。
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.warning import WarningRecord
from backend.models.config import WatchlistItem, MonitorItem
from backend.services.websocket_manager import ws_manager
from backend.utils.cache import MemoryCache

logger = logging.getLogger(__name__)

# A股概况数据缓存(6小时TTL)
a_share_cache = MemoryCache(maxsize=8, ttl=21600)

router = APIRouter(tags=["dashboard"], prefix="/dashboard")

# 延迟引用
_data_source_manager = None
_warning_engine = None


def _get_dsm():
    global _data_source_manager
    if _data_source_manager is None:
        from backend.main import data_source_manager
        _data_source_manager = data_source_manager
    return _data_source_manager


def _get_engine():
    global _warning_engine
    if _warning_engine is None:
        from backend.main import warning_engine
        _warning_engine = warning_engine
    return _warning_engine


async def _get_system_status() -> Dict[str, Any]:
    """获取系统状态摘要"""
    dsm = _get_dsm()
    engine = _get_engine()

    # 数据源状态
    data_sources = []
    try:
        data_sources = dsm.get_status_summary()
    except Exception as e:
        logger.warning(f"获取数据源状态失败: {e}")

    active_source = "unknown"
    try:
        active_source = dsm._active_name
    except Exception:
        pass

    # WebSocket连接数
    ws_count = ws_manager.count

    # 预警引擎状态
    engine_running = engine.is_running if engine else False
    monitor_count = len(engine._monitor_codes) if engine and hasattr(engine, '_monitor_codes') else 0

    return {
        "active_data_source": active_source,
        "data_sources": data_sources,
        "websocket_connections": ws_count,
        "warning_engine_running": engine_running,
        "monitor_stock_count": monitor_count,
        "timestamp": datetime.now().isoformat(),
    }


async def _get_market_overview() -> Dict[str, Any]:
    """获取大盘概览"""
    dsm = _get_dsm()

    INDEX_CODES = {
        "000001.SH": "上证指数",
        "399001.SZ": "深证成指",
        "399006.SZ": "创业板指",
        "000688.SH": "科创50",
        "000300.SH": "沪深300",
    }

    indices = []
    for code, name in INDEX_CODES.items():
        try:
            q = await dsm.get_quote(code)
            if q:
                indices.append({
                    "code": q.code,
                    "name": q.name,
                    "price": q.price,
                    "change_pct": q.change_pct,
                    "volume": q.volume,
                    "amount": q.amount,
                })
            else:
                indices.append({"code": code, "name": name, "price": None, "change_pct": None})
        except Exception as e:
            logger.warning(f"获取指数 {code} 失败: {e}")
            indices.append({"code": code, "name": name, "price": None, "change_pct": None, "error": str(e)})

    # 计算涨跌家数
    up_count = sum(1 for i in indices if i.get("change_pct") is not None and i["change_pct"] > 0)
    down_count = sum(1 for i in indices if i.get("change_pct") is not None and i["change_pct"] < 0)

    return {
        "indices": indices,
        "up_count": up_count,
        "down_count": down_count,
        "timestamp": datetime.now().isoformat(),
    }


async def _get_warning_summary(db: AsyncSession) -> Dict[str, Any]:
    """获取预警汇总统计"""
    # 按类型统计
    type_stmt = (
        select(
            WarningRecord.warning_type,
            WarningRecord.indicator_color,
            sa_func.count(WarningRecord.id)
        )
        .where(WarningRecord.is_acknowledged == False)
        .group_by(WarningRecord.warning_type, WarningRecord.indicator_color)
    )
    result = await db.execute(type_stmt)
    rows = result.all()

    # 构建统计
    by_type = {}
    by_level = {}
    total = 0
    # 初始化
    for wt in ["price", "updown", "trend", "resonance", "finance", "event", "risk", "decision"]:
        by_type[wt] = 0
    for lv in ["info", "warning", "danger", "critical"]:
        by_level[lv] = 0

    for row in rows:
        wtype, color, count = row
        count = count or 0
        total += count
        if wtype in by_type:
            by_type[wtype] = by_type.get(wtype, 0) + count
        # 颜色映射到级别
        level_map = {"gray": "info", "green": "info", "yellow": "warning", "red": "danger", "purple": "critical"}
        level = level_map.get(color, "info")
        by_level[level] = by_level.get(level, 0) + count

    # 获取最新预警
    latest_stmt = (
        select(WarningRecord)
        .where(WarningRecord.is_acknowledged == False)
        .order_by(WarningRecord.triggered_at.desc())
        .limit(5)
    )
    latest_result = await db.execute(latest_stmt)
    latest_warnings = [
        {
            "id": w.id,
            "code": w.code,
            "warning_type": w.warning_type,
            "warning_level": w.warning_level,
            "title": w.title,
            "indicator_color": w.indicator_color,
            "triggered_at": w.triggered_at.isoformat() if w.triggered_at else None,
        }
        for w in latest_result.scalars().all()
    ]

    return {
        "total": total,
        "by_type": by_type,
        "by_level": by_level,
        "latest_warnings": latest_warnings,
        "timestamp": datetime.now().isoformat(),
    }


async def _get_watchlist_snapshot(db: AsyncSession) -> Dict[str, Any]:
    """获取自选股/监控池快照"""
    # 自选股
    watchlist_result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.is_active == True)
        .order_by(WatchlistItem.sort_order)
        .limit(20)
    )
    watchlist_items = watchlist_result.scalars().all()

    # 监控池
    monitor_result = await db.execute(
        select(MonitorItem)
        .where(MonitorItem.is_active == True)
        .order_by(MonitorItem.id)
        .limit(20)
    )
    monitor_items = monitor_result.scalars().all()

    # 获取最近预警的股票列表
    recent_codes_stmt = (
        select(WarningRecord.code, sa_func.count(WarningRecord.id).label("cnt"))
        .where(WarningRecord.is_acknowledged == False)
        .group_by(WarningRecord.code)
        .order_by(sa_func.count(WarningRecord.id).desc())
        .limit(10)
    )
    recent_codes_result = await db.execute(recent_codes_stmt)
    alerted_stocks = [
        {"code": row.code, "warning_count": row.cnt}
        for row in recent_codes_result.all()
    ]

    return {
        "watchlist_count": len(watchlist_items),
        "watchlist": [
            {"code": item.code, "name": item.name, "sort_order": item.sort_order}
            for item in watchlist_items
        ],
        "monitor_count": len(monitor_items),
        "monitor": [
            {"code": item.code, "name": item.name, "monitor_type": item.monitor_type}
            for item in monitor_items
        ],
        "alerted_stocks": alerted_stocks,
        "timestamp": datetime.now().isoformat(),
    }


def _get_trading_session() -> Dict[str, Any]:
    """获取当前交易时段类型和倒计时（使用北京时间 Asia/Shanghai）"""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Asia/Shanghai")
    except Exception:
        # fallback：手工 UTC+8
        from datetime import timezone, timedelta
        tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    weekday = now.weekday()
    h, m, s = now.hour, now.minute, now.second
    current_sec = h * 3600 + m * 60 + s

    # 交易时段定义（秒数）
    PRE_AUCTION_START = 9 * 3600 + 15 * 60   # 09:15
    PRE_AUCTION_END = 9 * 3600 + 25 * 60      # 09:25
    MORNING_START = 9 * 3600 + 30 * 60        # 09:30
    MORNING_END = 11 * 3600 + 30 * 60         # 11:30
    AFTERNOON_START = 13 * 3600               # 13:00
    AFTERNOON_END = 15 * 3600                 # 15:00

    if weekday >= 5:  # 周六日
        return {"session": "weekend", "session_name": "休市(周末)", "countdown_seconds": 0,
                "next_open": "周一 09:30", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}

    if PRE_AUCTION_START <= current_sec < PRE_AUCTION_END:
        return {"session": "pre_open", "session_name": "集合竞价",
                "countdown_seconds": PRE_AUCTION_END - current_sec, "next_open": "", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}
    if MORNING_START <= current_sec < MORNING_END:
        return {"session": "morning", "session_name": "上午盘",
                "countdown_seconds": MORNING_END - current_sec, "next_open": "", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}
    if AFTERNOON_START <= current_sec < AFTERNOON_END:
        return {"session": "afternoon", "session_name": "下午盘",
                "countdown_seconds": AFTERNOON_END - current_sec, "next_open": "", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}
    # 非交易时段
    if current_sec < MORNING_START:
        return {"session": "pre_market", "session_name": "盘前",
                "countdown_seconds": MORNING_START - current_sec, "next_open": "", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}
    else:
        return {"session": "closed", "session_name": "已收盘",
                "countdown_seconds": 0, "next_open": "下一个交易日 09:30", "current_time": now.strftime("%Y-%m-%d %H:%M:%S")}


async def _get_latest_analysis() -> Dict[str, Any]:
    """获取最近分析结论"""
    try:
        from backend.models.analysis import AnalysisReport
        from backend.config.database import async_session_factory

        async with async_session_factory() as session:
            stmt = (
                select(AnalysisReport)
                .where(AnalysisReport.status == "completed")
                .order_by(AnalysisReport.created_at.desc())
                .limit(3)
            )
            result = await session.execute(stmt)
            reports = result.scalars().all()
            return {
                "reports": [
                    {
                        "id": r.id,
                        "report_type": r.report_type,
                        "title": r.title,
                        "summary": r.summary,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in reports
                ],
                "total": len(reports),
            }
    except Exception as e:
        logger.warning(f"获取分析结论失败: {e}")
        return {"reports": [], "total": 0, "note": "分析模块尚未启用"}


# ─── A股概况 ───

A_SHARE_PREFIXES = {
    "shanghai": {
        "main_board": ["600", "601", "603", "605"],
        "star": ["688"],
        "b_share": ["900"],
    },
    "shenzhen": {
        "main_board": ["000", "001", "002", "003", "004"],
        "gem": ["300", "301"],
        "b_share": ["200"],
    },
    "beijing": {
        "all": ["920", "430", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873"],
    },
}

ETF_PREFIXES = {
    "shanghai": ["51", "52", "56", "58"],
    "shenzhen": ["159"],
}


def _parse_sina_stock_json(text: str) -> list:
    """解析Sina股票JSON响应(可能带括号或不带)"""
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        t = t[1:-1]
    if not t or t == "[]":
        return []
    import json
    return json.loads(t)


def _fetch_sina_page(client, node: str, page: int, num: int = 100) -> list:
    """调用Sina MarketCenter.getHQNodeData单页获取股票数据"""
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
    params = {"page": str(page), "num": str(num), "sort": "code", "asc": "1", "node": node}
    resp = client.get(url, params=params, headers={"User-Agent": "Mozilla/5.0",
                "Referer": "https://vip.stock.finance.sina.com.cn/"})
    return _parse_sina_stock_json(resp.text)


def _fetch_all_sina_codes() -> list:
    """通过Sina MarketCenter API分页获取全市场A股+北交所股票代码（含B股）"""
    import httpx
    all_codes = []
    seen = set()
    nodes = ["sh_a", "sz_a", "bj_a", "sh_b", "sz_b"]
    with httpx.Client(timeout=30, verify=False) as client:
        for node in nodes:
            page = 1
            empty_pages = 0
            while page <= 200:
                try:
                    items = _fetch_sina_page(client, node, page, 100)
                except Exception as e:
                    logger.warning(f"Sina {node} 第{page}页失败: {e}")
                    break
                if not items:
                    empty_pages += 1
                    if empty_pages >= 3:
                        break
                    page += 1
                    continue
                empty_pages = 0
                for item in items:
                    sym = str(item.get("symbol", "")).strip()
                    code = sym[2:] if sym.startswith(("sh", "sz", "bj")) else sym
                    if code and code not in seen:
                        seen.add(code)
                        all_codes.append(code)
                if len(items) < 100:
                    break
                page += 1
        logger.info(f"Sina API: 共获取 {len(all_codes)} 个代码 (nodes={nodes})")
    return all_codes


def _fetch_all_codes_by_akshare() -> list:
    """通过AKShare获取全市场股票代码（含北交所），替代Sina在Docker中被封的问题"""
    try:
        import akshare as _ak
        import pandas as _pd
        df = _ak.stock_info_a_code_name()
        if df is not None and not df.empty:
            codes = df['code'].astype(str).str.strip().tolist()
            logger.info(f"AKShare: 共获取 {len(codes)} 个代码")
            return codes
    except Exception as e:
        logger.warning(f"AKShare股票列表获取失败: {e}")
    return []


def _fetch_etf_count() -> dict:
    """获取ETF数量统计（东方财富push2，备用AKShare）"""
    etf_sh = 0
    etf_sz = 0
    
    # 主用：东方财富 push2
    try:
        import httpx as _hx
        _url = "https://push2.eastmoney.com/api/qt/clist/get"
        _params = {
            "pn": "1", "pz": "5000", "po": "1", "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2", "invt": "2", "fid": "f3",
            "fs": "m:0+t:3",
            "fields": "f12",
        }
        _hdrs = {"User-Agent": "Mozilla/5.0"}
        with _hx.Client(timeout=15) as _cl:
            _r = _cl.get(_url, params=_params, headers=_hdrs)
            _d = _r.json()
            _diff = _d.get("data", {}).get("diff", [])
            for _i in _diff:
                c = str(_i.get("f12", ""))
                if c.startswith(("51", "52", "56", "58")):
                    etf_sh += 1
                elif c.startswith("159"):
                    etf_sz += 1
        logger.info(f"ETF: 沪{etf_sh}+深{etf_sz}={etf_sh+etf_sz}")
    except Exception as e:
        logger.warning(f"ETF东财获取失败: {e}")
    
    # 备用：AKShare
    if etf_sh + etf_sz == 0:
        try:
            import akshare as _ak
            df = _ak.fund_etf_spot_em()
            if df is not None and not df.empty:
                for c in df['代码'].astype(str):
                    if c.startswith(("51", "52", "56", "58")):
                        etf_sh += 1
                    elif c.startswith("159"):
                        etf_sz += 1
                logger.info(f"ETF(AKShare): 沪{etf_sh}+深{etf_sz}={etf_sh+etf_sz}")
        except Exception as e2:
            logger.warning(f"ETF AKShare备用也失败: {e2}")
    
    return {
        "shanghai": {"count": etf_sh, "prefixes": ["51", "52", "56", "58"]},
        "shenzhen": {"count": etf_sz, "prefixes": ["159"]},
        "total": etf_sh + etf_sz,
    }


def _fetch_a_share_codes_sync() -> dict:
    """
    同步获取全市场股票代码并统计(在executor中运行)。
    主用：Sina MarketCenter API（分页获取全市场股票代码和名称）。
    备用：从本地缓存文件读取。
    结果缓存在磁盘和内存中。
    """
    import json as jmod
    from pathlib import Path

    cache_dir = Path("./data/a_share_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "stock_codes.json"

    # 尝试从本地缓存读取
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = jmod.load(f)
            if cached and cached.get("total_stock_count", 0) > 100:
                logger.info(f"A股概况: 使用磁盘缓存 {cached.get('total_stock_count', 0)} 只")
                return cached
        except Exception:
            pass

    all_codes = []
    
    # 主用：AKShare（含北交所，Docker兼容性好）
    try:
        all_codes = _fetch_all_codes_by_akshare()
        if all_codes:
            logger.info(f"A股概况: AKShare返回 {len(all_codes)} 只")
    except Exception as e:
        logger.warning(f"A股概况: AKShare失败 ({e})")

    # 备用：新浪 MarketCenter API
    if not all_codes:
        try:
            all_codes = _fetch_all_sina_codes()
            if all_codes:
                logger.info(f"A股概况: Sina API返回 {len(all_codes)} 只")
        except Exception as e:
            logger.warning(f"A股概况: Sina API失败 ({e})")

    # 备用2：东方财富（含北交所 m:0 t:82）
    if not all_codes:
        try:
            import math as _mh
            import httpx as _hx
            _url = "https://push2.eastmoney.com/api/qt/clist/get"
            _base = {
                "pn": "1", "pz": "5000", "po": "1", "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2", "invt": "2", "fid": "f3",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81,m:0 t:82",
                "fields": "f12",
            }
            _hdrs = {"User-Agent": "Mozilla/5.0"}
            with _hx.Client(timeout=30) as _cl:
                _r = _cl.get(_url, params=_base, headers=_hdrs)
                _d = _r.json()
                _total = _d.get("data", {}).get("total", 0) or 0
                _diff = _d.get("data", {}).get("diff", [])
                all_codes.extend([_i["f12"] for _i in _diff])
                if _total > len(_diff):
                    _base2 = dict(_base, pz="100")
                    _pages = _mh.ceil(_total / 100)
                    for _p in range(2, _pages + 1):
                        try:
                            _p2 = dict(_base2, pn=str(_p))
                            _r2 = _cl.get(_url, params=_p2, headers=_hdrs)
                            all_codes.extend([_i["f12"] for _i in _r2.json()["data"]["diff"]])
                        except Exception:
                            pass
            if all_codes:
                logger.info(f"A股概况: 东财备用返回 {len(all_codes)} 只")
        except Exception as e:
            logger.error(f"A股概况: 东财备用也失败 ({e})")

    if not all_codes:
        logger.error("A股概况: 所有数据源均失败")
        return {"error": "所有数据源均不可用", "total_stock_count": 0, "etf": {"total": 0}}

    # 统计
    result = _count_by_prefix(all_codes)
    result["total_stock_count"] = len(all_codes)
    logger.info(f"A股概况: 统计结果 sh={result.get('shanghai',{}).get('total','?')}, sz={result.get('shenzhen',{}).get('total','?')}, bj={result.get('beijing',{}).get('total','?')}")

    # ETF统计（通过akshare fund_etf_spot_em 或 东财push2）
    try:
        etf_info = _fetch_etf_count()
        result["etf"] = etf_info
        logger.info(f"A股概况: ETF {etf_info.get('total', 0)}")
    except Exception as e:
        logger.warning(f"A股概况: ETF获取失败 ({e})")
        result["etf"] = {"shanghai": {"count": 0}, "shenzhen": {"count": 0}, "total": 0}

    # 写入磁盘缓存
    # 写入磁盘缓存（如果北交所/ETF数据为空但旧缓存有数据，保留旧数据）
    if result.get("beijing",{}).get("total",0) == 0 or result.get("etf",{}).get("total",0) == 0:
        try:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as _f:
                    _old = jmod.load(_f)
                if _old.get("beijing",{}).get("total",0) > 0 and result.get("beijing",{}).get("total",0) == 0:
                    result["beijing"] = _old["beijing"]
                if _old.get("etf",{}).get("total",0) > 0 and result.get("etf",{}).get("total",0) == 0:
                    result["etf"] = _old["etf"]
        except Exception:
            pass
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            jmod.dump(result, f, ensure_ascii=False, default=str)
    except Exception:
        pass

    return result


def _count_by_prefix(codes: list) -> dict:
    """按代码前缀统计各类股票数量"""
    sh_main = sh_star = sh_b = 0
    sz_main = sz_gem = sz_b = 0
    bj = 0

    # ETF计数单独处理（基金代码列表）
    # 以下只统计股票型代码
    for code in codes:
        code = str(code).strip()
        if not code:
            continue
        if code.startswith(("600", "601", "603", "605")):
            sh_main += 1
        elif code.startswith("688"):
            sh_star += 1
        elif code.startswith("689"):
            sh_star += 1
        elif code.startswith("900"):
            sh_b += 1
        elif code.startswith(("000", "001", "002", "003", "004", "302")):
            sz_main += 1
        elif code.startswith(("300", "301")):
            sz_gem += 1
        elif code.startswith("200"):
            sz_b += 1
        elif code.startswith(("920", "430", "830", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873")):
            bj += 1

    return {
        "shanghai": {
            "total": sh_main + sh_star + sh_b,
            "main_board": {"count": sh_main, "prefixes": ["600", "601", "603", "605"]},
            "star": {"count": sh_star, "prefixes": ["688"]},
            "b_share": {"count": sh_b, "prefixes": ["900"]},
        },
        "shenzhen": {
            "total": sz_main + sz_gem + sz_b,
            "main_board": {"count": sz_main, "prefixes": ["000", "001", "002", "003", "004"]},
            "gem": {"count": sz_gem, "prefixes": ["300", "301"]},
            "b_share": {"count": sz_b, "prefixes": ["200"]},
        },
        "beijing": {
            "total": bj,
            "all": {"count": bj, "prefixes": ["920"]},
        },
        "generated_at": datetime.now().isoformat(),
    }


# ─── ST股票列表 ───

@router.get("/st-list")
async def get_st_stock_list():
    """
    ST股票列表(风险警示板)。
    来源:东方财富行情中心,缓存6小时。
    """
    cached = a_share_cache.get("st_list")
    if cached:
        return cached

    def _fetch():
        from datetime import datetime
        import json, urllib.request
        _t0 = datetime.now()
        try:
            items = []
            # 用新浪API获取沪深两市股票列表,过滤ST股票
            # 新浪API对Python HTTP库兼容性最好
            for node in ["sh_a", "sz_a"]:
                url = ('https://vip.stock.finance.sina.com.cn/quotes_service/'
                       'api/json_v2.php/Market_Center.getHQNodeDataSimple?'
                       'page=1&num=10000&sort=symbol&asc=1&node=' + node)
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://vip.stock.finance.sina.com.cn/',
                })
                try:
                    resp = urllib.request.urlopen(req, timeout=20)
                    text = resp.read().decode('gbk')
                    # 新浪返回带括号的JSON数组: [...]
                    if text.startswith('(') and text.endswith(')'):
                        text = text[1:-1]
                    data = json.loads(text)
                    for item in data:
                        name = str(item.get('name', ''))
                        if 'ST' in name or '*ST' in name or 'S*ST' in name:
                            code = str(item.get('symbol', '')).replace('sh','').replace('sz','')
                            try:
                                price = float(item.get('trade', 0)) if item.get('trade') else None
                            except:
                                price = None
                            try:
                                change_pct = float(item.get('changepercent', 0)) if item.get('changepercent') else None
                            except:
                                change_pct = None
                            st_type = '*ST' if name.startswith('*ST') else ('S*ST' if name.startswith('S*ST') else 'ST')
                            items.append({
                                'code': code, 'name': name, 'st_type': st_type,
                                'price': price, 'change_pct': change_pct,
                            })
                except Exception as e2:
                    logger.warning(f"ST列表: 新浪{node}请求失败: {e2}")
                    continue
            _elapsed = (datetime.now() - _t0).total_seconds()
            logger.info(f"ST股票列表完成: {len(items)}只(新浪), {_elapsed:.1f}s")
            return {"items": items, "count": len(items), "generated_at": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"获取ST股票列表失败: {e}")
            return {"error": str(e), "items": [], "count": 0, "generated_at": datetime.now().isoformat()}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch)
    a_share_cache.set("st_list", result)
    return result


@router.get("/st-detail/{code}")
async def get_st_stock_detail(code: str):
    """
    ST股票详情:从巨潮资讯网搜索ST相关公告,提取ST原因。
    """
    def _fetch_detail():
        from datetime import datetime as _dt
        from datetime import timedelta
        import httpx
        try:
            url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
            headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            today_str = _dt.now().strftime("%Y-%m-%d")
            one_year_ago = (_dt.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            se_date = f"{one_year_ago}~{today_str}"
            # 搜索ST相关公告
            reasons = []
            with httpx.Client(timeout=25) as client:
                for kw in ["被实施退市风险警示", "实施其他风险警示"]:
                    for plate in ["sz", "sh"]:
                        pdata = {"pageNum": "1", "pageSize": "30", "column": "szse", "tabName": "fulltext",
                                 "plate": plate, "stock": "", "searchkey": kw, "secid": "", "category": "",
                                 "trade": "", "seDate": se_date, "sortName": "", "sortType": "",
                                 "isHLtitle": "true"}
                        try:
                            r = client.post(url, data=pdata, headers=headers)
                            result = r.json()
                            anns = result.get("announcements") or []
                            for ann in anns:
                                if ann.get("secCode", "") != code:
                                    continue
                                ts = ann.get("announcementTime", 0)
                                date_str = _dt.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else ""
                                title = ann.get("announcementTitle", "").replace("<em>", "").replace("</em>", "")
                                reason = _extract_st_reason(title)
                                reasons.append({"title": title, "date": date_str, "reason": reason,
                                                "url": f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={ann.get('announcementId', '')}"})
                        except Exception:
                            continue
            # 去重
            seen = set()
            unique = []
            for r in reasons:
                key = r["reason"] or r["title"][:30]
                if key not in seen:
                    seen.add(key)
                    unique.append(r)
            # 按日期降序
            unique.sort(key=lambda x: x["date"] or "", reverse=True)
            return {"code": code, "st_reasons": unique, "count": len(unique)}
        except Exception as e:
            logger.error(f"获取ST {code} 详情失败: {e}")
            return {"code": code, "error": str(e), "st_reasons": [], "count": 0}

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_detail)


def _extract_st_reason(title: str) -> str:
    """从公告标题中提取ST原因"""
    t = title
    # 常见ST原因关键词
    patterns = [
        ("净利润为负且营业收入低于1亿元", "净利润为负且营收<1亿"),
        ("扣除非经常性损益前后净利润", "扣非净利为负"),
        ("净资产为负", "净资产为负"),
        ("无法表示意见", "财报被出具无法表示意见"),
        ("否定意见", "财报被出具否定意见"),
        ("资金占用", "资金占用"),
        ("违规担保", "违规担保"),
        ("持续经营能力", "持续经营能力存疑"),
        ("主要银行账户被冻结", "主要银行账户冻结"),
        ("内部控制", "内部控制缺陷"),
        ("信息披露", "信息披露违规"),
        ("重整", "法院裁定受理重整"),
        ("破产", "破产"),
        ("停产", "停产"),
        ("债务违约", "债务违约"),
    ]
    for pat, reason in patterns:
        if pat in t:
            return reason
    # 通用判断
    if "退市风险" in t:
        return "退市风险警示"
    if "其他风险" in t:
        return "其他风险警示"
    if "叠加" in t:
        return "叠加实施风险警示"
    if "ST" in t or "st" in t.lower():
        return "ST风险警示"
    return ""  # 不明确的返回空


@router.get("/a-share-overview")
async def get_a_share_overview():
    """
    A股概况:按交易所/板块统计股票数量。

    返回沪市(主板/科创板/B股)、深市(主板/创业板/B股)、
    北交所、新股申购的分类统计。
    数据来源:AKShare / Sina API,日缓存6小时。
    """
    # 检查内存缓存
    cached = a_share_cache.get("a_share_overview")
    if cached:
        return cached

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _fetch_a_share_codes_sync)
        a_share_cache.set("a_share_overview", result)
        return result
    except Exception as e:
        logger.error(f"获取A股概况失败: {e}")
        return {
            "error": str(e),
            "shanghai": {"total": 0, "main_board": {"count": 0}, "star": {"count": 0}, "b_share": {"count": 0}},
            "shenzhen": {"total": 0, "main_board": {"count": 0}, "gem": {"count": 0}, "b_share": {"count": 0}},
            "beijing": {"total": 0, "all": {"count": 0, "prefixes": ["920"]}},
            "etf": {"shanghai": {"count": 0}, "shenzhen": {"count": 0}, "total": 0},
            "total_stock_count": 0,
            "generated_at": datetime.now().isoformat(),
        }


def _get_a_share_overview() -> Dict[str, Any]:
    """从内存缓存/磁盘缓存获取A股概况数据。
    优先读内存缓存(要求数据完整北交所>0)，否则读磁盘缓存。"""
    cached = a_share_cache.get("a_share_overview")
    if cached:
        bj = cached.get("beijing",{}).get("total",0)
        et = cached.get("etf",{}).get("total",0)
        if bj > 0 or et > 0:
            return {
                "beijing": cached["beijing"],
                "etf": cached.get("etf", {"shanghai":{"count":0},"shenzhen":{"count":0},"total":0}),
            }
    # 磁盘缓存兜底
    try:
        import json as _jmod
        _f = "data/a_share_cache/stock_codes.json"
        from pathlib import Path as _P; import json as _jmod2
        if _P(_f).exists():
            with open(_f, "r", encoding="utf-8") as _fh:
                _dc = _jmod.load(_fh)
            if _dc and _dc.get("beijing",{}).get("total",0) > 0:
                return {
                    "beijing": _dc["beijing"],
                    "etf": _dc.get("etf", {"shanghai":{"count":0},"shenzhen":{"count":0},"total":0}),
                }
    except Exception:
        pass
    return {
        "beijing": {"total": 0, "all": {"count": 0, "prefixes": ["920"]}},
        "etf": {"shanghai": {"count": 0}, "shenzhen": {"count": 0}, "total": 0},
    }


# ─── 决策仪表盘 ───

@router.get("/decision-board")
async def get_decision_board():
    """
    决策仪表盘：对监控股逐个计算量化评分，生成买卖建议。
    不依赖AI，纯算法计算。

    返回：
      stocks: 股票决策列表，按评分排序
      stats: 统计（看多家数/看空家数/平均分）
    """
    from backend.api.market import _get_dsm
    from backend.services.anomaly_detector import batch_detect_anomalies
    from backend.services.data_source.base import KLineData as _KLine

    dsm = _get_dsm()
    import sys
    
    # 自动重置数据源（解决后台定时任务累计失败导致数据源被误标记为OFFLINE的问题）
    dsm.reset_source_status()
    print(f"[QB] reset done. Sources:", {n: f'{s.status}/{s._consecutive_failures}' for n,s in dsm._sources.items()}, file=sys.stderr)
    
    # 1. 读取监控池
    from sqlalchemy import select as _sl
    from backend.config.database import async_session_factory
    from backend.models.config import MonitorItem
    codes = []
    try:
        async with async_session_factory() as _db:
            _r = await _db.execute(_sl(MonitorItem).where(MonitorItem.is_active == True))
            codes = [i.code for i in _r.scalars().all()]
    except Exception:
        pass
    if not codes:
        return {"stocks": [], "stats": {"bullish": 0, "bearish": 0, "neutral": 0, "avg_score": 0}}

    # 去重
    codes = list(dict.fromkeys(codes))

    # 2. 批量获取行情
    quotes = await dsm.get_quotes(codes)
    if not quotes:
        import sys
        print(f"[QB_DBG] quotes empty, codes={codes}, active={dsm._active_name}", file=sys.stderr)
        return {"stocks": [], "stats": {"bullish": 0, "bearish": 0, "neutral": 0, "avg_score": 0}}
    print(f"[QB_DBG] quotes OK: {len(quotes)} items", file=sys.stderr)

    quote_map = {q.code: q for q in quotes}

    # 3. 批量获取K线 + 异动
    import asyncio
    kline_tasks = [dsm.get_kline(c, 60) for c in codes]
    kline_results = await asyncio.gather(*kline_tasks, return_exceptions=True)
    import sys
    for i, (c, kr) in enumerate(zip(codes, kline_results)):
        if isinstance(kr, Exception):
            print(f"[QB_DBG] kline {c}: EXCEPTION {kr}", file=sys.stderr)
        elif not kr:
            print(f"[QB_DBG] kline {c}: EMPTY", file=sys.stderr)
        else:
            print(f"[QB_DBG] kline {c}: {len(kr)} bars, last={kr[-1].trade_date} close={kr[-1].close_price}", file=sys.stderr)
    
    anomalies = await batch_detect_anomalies(quotes, dsm)

    # 4. 逐只评分
    from backend.utils.indicators import calc_ma, calc_macd, calc_kdj, calc_rsi

    decisions = []
    for code, klines_raw in zip(codes, kline_results):
        q = quote_map.get(code)
        if isinstance(klines_raw, Exception):
            continue
        if not klines_raw or len(klines_raw) < 20:
            continue

        closes = [k.close_price for k in klines_raw]
        highs = [k.high_price for k in klines_raw]
        lows = [k.low_price for k in klines_raw]
        volumes = [k.volume for k in klines_raw]

        # Fallback: use latest K-line close if real-time quote unavailable
        if not q:
            last_k = klines_raw[-1]
            prev_k = klines_raw[-2] if len(klines_raw) >= 2 else None
            price = last_k.close_price or 0
            pre_close = prev_k.close_price if prev_k else price
            change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0
            volume = last_k.volume or 0
            name = code
            class FallbackQuote:
                pass
            q = FallbackQuote()
            q.code = code
            q.price = price
            q.pre_close = pre_close
            q.change_pct = change_pct
            q.volume = volume
            q.turnover_rate = 0
            q.name = name
            q.open_price = last_k.open_price or price
            q.high_price = last_k.high_price or price
            q.low_price = last_k.low_price or price

        # ── 趋势评分 (0-30) ──
        ma5 = calc_ma(closes, 5)[-1] if len(closes) >= 5 else 0
        ma10 = calc_ma(closes, 10)[-1] if len(closes) >= 10 else 0
        ma20 = calc_ma(closes, 20)[-1] if len(closes) >= 20 else 0
        ma60 = calc_ma(closes, 60)[-1] if len(closes) >= 60 else 0

        trend_score = 0
        trend_detail = ""
        if ma5 and ma10 and ma20 and ma60 and ma10 > ma20 > ma60:
            trend_score = 30 if ma5 > ma10 else 25
            trend_detail = "多头排列"
        elif ma5 and ma10 and ma5 > ma10:
            trend_score = 15
            trend_detail = "短多"
        elif ma5 and ma10 and ma5 < ma10:
            trend_score = 5
            trend_detail = "短空"
        else:
            trend_detail = "震荡"

        # ── 动量评分 (0-25) ──
        momentum_score = 0
        if len(closes) >= 26:
            macd_data = calc_macd(closes)
            dif = macd_data.get("dif", [])
            dea = macd_data.get("dea", [])
            macd_hist = macd_data.get("macd_histogram", [])
            if dif and dea and len(dif) >= 2 and len(dea) >= 2:
                if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
                    momentum_score += 10  # MACD金叉
                elif dif[-1] > dea[-1]:
                    momentum_score += 5  # DIF > DEA

        kdj_data = calc_kdj(highs, lows, closes)
        k_arr = kdj_data.get("k", [])
        d_arr = kdj_data.get("d", [])
        k = k_arr[-1] if k_arr else 0
        d = d_arr[-1] if d_arr else 0
        if k and d:
            if k > d and k < 80:
                momentum_score += 8  # KDJ健康上行
            elif k > d:
                momentum_score += 4

        rsi6_arr = calc_rsi(closes, 6)
        rsi_val = rsi6_arr[-1] if rsi6_arr else 0
        if rsi_val:
            if 30 < rsi_val < 70:
                momentum_score += 7  # RSI健康
            elif rsi_val >= 70:
                momentum_score += 3  # 超买

        # ── 量价评分 (0-20) ──
        volume_score = 0
        if q.volume and len(volumes) >= 5:
            avg_vol = sum(volumes[-5:]) / 5
            vol_ratio = q.volume / avg_vol if avg_vol > 0 else 1
            if vol_ratio > 1.5:
                volume_score += 10
            elif vol_ratio > 1.0:
                volume_score += 5
            if q.turnover_rate and 3 < q.turnover_rate < 15:
                volume_score += 10
            elif q.turnover_rate and 1 < q.turnover_rate <= 3:
                volume_score += 5

        # ── 风险评分 (0-25) ──
        risk_score = 15  # 基础分
        stock_anomalies = anomalies.get(code, [])
        for a in stock_anomalies:
            if a.get("type") == "bearish":
                risk_score -= 5
            elif a.get("type") == "bullish":
                risk_score += 3
        risk_score = max(0, min(25, risk_score))

        total_score = min(100, trend_score + momentum_score + volume_score + risk_score)

        # ── 信号判定 ──
        signal_type = "neutral"
        action_text = "观望"
        if total_score >= 65:
            signal_type = "bullish"
            action_text = "关注/持有"
        elif total_score >= 45:
            signal_type = "neutral"
            action_text = "观望"
        else:
            signal_type = "bearish"
            action_text = "规避"

        decisions.append({
            "code": code,
            "name": q.name or code,
            "price": q.price,
            "change_pct": q.change_pct,
            "total_score": total_score,
            "signal_type": signal_type,
            "action": action_text,
            "scores": {
                "trend": trend_score,
                "momentum": momentum_score,
                "volume": volume_score,
                "risk": risk_score,
            },
            "details": {
                "trend": trend_detail,
                "ma5": round(ma5, 2) if ma5 else None,
                "ma10": round(ma10, 2) if ma10 else None,
                "ma20": round(ma20, 2) if ma20 else None,
                "anomalies": [a["name"] for a in stock_anomalies],
            },
        })

    # 排序
    decisions.sort(key=lambda x: x["total_score"], reverse=True)

    bullish = sum(1 for d in decisions if d["signal_type"] == "bullish")
    bearish = sum(1 for d in decisions if d["signal_type"] == "bearish")
    neutral = sum(1 for d in decisions if d["signal_type"] == "neutral")
    avg_score = round(sum(d["total_score"] for d in decisions) / len(decisions), 1) if decisions else 0

    return {
        "stocks": decisions,
        "stats": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "avg_score": avg_score,
            "total": len(decisions),
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    仪表盘聚合数据。

    整合M02/M03/M05/M06模块数据。
    返回系统状态摘要、大盘概览、预警汇总、自选/监控池快照、最近分析结论。
    """
    system_status = await _get_system_status()
    market_overview = await _get_market_overview()
    warning_summary = await _get_warning_summary(db)
    watchlist_snapshot = await _get_watchlist_snapshot(db)
    latest_analysis = await _get_latest_analysis()
    trading_session = _get_trading_session()
    a_share_overview = _get_a_share_overview()

    return {
        "system_status": system_status,
        "market_overview": market_overview,
        "warning_summary": warning_summary,
        "watchlist_snapshot": watchlist_snapshot,
        "latest_analysis": latest_analysis,
        "trading_session": trading_session,
        **a_share_overview,
        "generated_at": datetime.now().isoformat(),
    }


# ─── 突发事件 ───

@router.get("/event-stocks")
async def get_event_stocks():
    """
    突发事件股票列表(9类负面事件)。
    来源:巨潮资讯网公告检索,缓存6小时。
    """
    cached = a_share_cache.get("event_stocks")
    if cached:
        return cached

    loop = asyncio.get_event_loop()
    from backend.services.event_detector import fetch_all_events as _fe
    try:
        result = await loop.run_in_executor(None, _fe)
        a_share_cache.set("event_stocks", result)
        return result
    except Exception as e:
        logger.error(f"获取突发事件失败: {e}")
        return {"error": str(e), "items": [], "count": 0, "generated_at": datetime.now().isoformat()}
