"""
M02 实时行情模块API — 完整实现。

遵循架构方案4.1节 M02 行情接口定义 + 7.2/7.3节实时性保障与降级策略：
- GET /api/v1/market/overview           → 大盘概览（从 data_source 获取）
- GET /api/v1/market/quotes/{codes}     → 批量行情（多只股票实时行情）
- GET /api/v1/market/kline/{code}       → K线数据（日线/分钟线）
- GET /api/v1/market/premarket          → 盘前提示概览（阶段4集成AI）
- POST /api/v1/market/premarket/generate → 生成盘前提示（阶段4集成AI）

数据源自动降级链路：通达信(主) → 新浪(备1) → 东方财富(备2)

遵循原则②：所有行情数据从 data_source 实时获取，不硬编码。
遵循原则③：严格按架构方案中接口定义实现。
"""

import logging
import json
import os
import re
import asyncio
import httpx
from typing import List, Optional, Dict, Any, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config.database import get_db

from backend.services.data_source.base import QuoteData
from backend.services.data_source.fallback import DataSourceUnavailableError

# 延迟获取 data_source_manager
_data_source_manager = None

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market"], prefix="/market")


def _get_dsm():
    """延迟获取数据源管理器"""
    global _data_source_manager
    if _data_source_manager is None:
        from backend.main import data_source_manager
        _data_source_manager = data_source_manager
    return _data_source_manager


# 主要指数代码映射
INDEX_CODES = {
    "000001.SH": "上证指数",
    "399001.SZ": "深证成指",
    "399006.SZ": "创业板指",
    "000688.SH": "科创50",
    "000300.SH": "沪深300",
    "000016.SH": "上证50",
    "000905.SH": "中证500",
    "899050.BJ": "北证50",
    "899601.BJ": "北证专精特新",
}


# ─── 大盘概览 ─────────────────────────────────────────

@router.get("/overview")
async def market_overview():
    """
    大盘概览。

    返回主要指数的实时概况。
    数据源自动降级：tdx_local → eastmoney → sina
    使用批量查询接口获取所有指数（比单个查询更快且兼容东财API）
    """
    dsm = _get_dsm()
    errors = []

    # 使用批量接口一次获取所有指数
    index_codes = [code.split(".")[0] for code in INDEX_CODES.keys()]
    quotes_data = []
    try:
        quotes = await dsm.get_quotes(index_codes)
        if quotes:
            qmap = {q.code: q for q in quotes}
            for raw_code, name in INDEX_CODES.items():
                clean_code = raw_code.split(".")[0]
                q = qmap.get(clean_code)
                if q:
                    quotes_data.append({
                        "code": raw_code,
                        "name": q.name,
                        "price": q.price,
                        "change": q.change,
                        "change_pct": q.change_pct,
                        "open": q.open_price if q.open_price else None,
                        "high": q.high_price if q.high_price else None,
                        "low": q.low_price if q.low_price else None,
                        "pre_close": q.pre_close if q.pre_close else None,
                        "volume": q.volume,
                        "amount": q.amount,
                    })
                else:
                    quotes_data.append({
                        "code": raw_code, "name": name,
                        "price": None, "change": None, "change_pct": None,
                        "open": None, "high": None, "low": None,
                        "pre_close": None, "volume": None, "amount": None,
                        "note": "数据暂不可用",
                    })
        else:
            # 批量查询全部失败，逐个查询降级
            for code, name in INDEX_CODES.items():
                try:
                    q = await dsm.get_quote(code)
                    if q:
                        quotes_data.append({...})
                    else:
                        quotes_data.append({
                            "code": code, "name": name,
                            "price": None, "change": None, "change_pct": None,
                            "note": "数据暂不可用",
                        })
                except Exception as e:
                    logger.warning(f"获取指数 {code} 失败: {e}")
                    errors.append({"code": code, "error": str(e)})
                    quotes_data.append({"code": code, "name": name,
                        "price": None, "note": f"失败: {str(e)}"})
    except Exception as e:
        logger.error(f"批量获取指数行情失败: {e}")
        errors.append(str(e))
        for code, name in INDEX_CODES.items():
            quotes_data.append({"code": code, "name": name,
                "price": None, "note": f"数据获取失败"})

    try:
        active_source = dsm._active_name if hasattr(dsm, '_active_name') else "unknown"
    except Exception:
        active_source = "unknown"

    return {
        "items": quotes_data,
        "timestamp": datetime.now().isoformat(),
        "active_data_source": active_source,
        "total": len(quotes_data),
        "error_count": len(errors),
    }


# ─── 批量行情 ─────────────────────────────────────────

@router.get("/quotes")
async def batch_quotes_all(
    request: Request = None,
):
    """
    批量行情（不传代码时，从监控池读取股票列表）。
    按设计文档 3.2.2 节：监控范围 = 监控股票池股票。
    按登录用户隔离显示各自监控池。
    """
    from sqlalchemy import select
    from backend.config.database import async_session_factory
    from backend.models.config import MonitorItem
    from backend.services.auth_service import decode_token

    # 从请求头解析当前用户
    user_id = 0
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = decode_token(auth[7:])
            if payload:
                try:
                    user_id = int(payload.get("sub", 0))
                except (ValueError, TypeError):
                    user_id = 0

    codes = []
    try:
        async with async_session_factory() as db:
            query = select(MonitorItem).where(MonitorItem.is_active == True)
            if user_id > 0:
                query = query.where(MonitorItem.user_id == user_id)
            result = await db.execute(query)
            codes = [item.code for item in result.scalars().all()]
    except Exception as e:
        logger.warning(f"读取监控池失败: {e}")

    if not codes:
        return {"codes": [], "quotes": [], "count": 0, "timestamp": None, "source": "monitor_pool"}

    return await _fetch_quotes_by_codes(codes, source="monitor_pool")


@router.get("/watchlist-quotes")
async def batch_watchlist_quotes(
    request: Request = None,
):
    """
    自选股批量行情（从 WatchlistItem 读取股票列表）。
    跟监控池独立的股票池，在系统设置中管理。
    按登录用户隔离：admin 看 admin 的自选股，demo 看 demo 的。
    """
    from sqlalchemy import select
    from backend.config.database import async_session_factory
    from backend.models.config import WatchlistItem
    from backend.services.auth_service import decode_token

    # 从请求头解析当前用户
    user_id = 0
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = decode_token(auth[7:])
            if payload:
                try:
                    user_id = int(payload.get("sub", 0))
                except (ValueError, TypeError):
                    user_id = 0

    codes = []
    try:
        async with async_session_factory() as db:
            query = select(WatchlistItem).where(WatchlistItem.is_active == True)
            if user_id > 0:
                query = query.where(WatchlistItem.user_id == user_id)
            result = await db.execute(query)
            codes = [item.code for item in result.scalars().all()]
    except Exception as e:
        logger.warning(f"读取自选股池失败: {e}")

    if not codes:
        return {"codes": [], "quotes": [], "count": 0, "timestamp": None, "source": "watchlist"}

    # 使用dsm.get_quotes()自动降级（与监控池/quotes接口一致）
    dsm = _get_dsm()
    quotes_data = []
    errors = []
    try:
        result = await dsm.get_quotes(codes)
        if result:
            for q in result:
                quotes_data.append({
                    "code": q.code, "name": q.name,
                    "price": q.price, "open": q.open_price,
                    "high": q.high_price, "low": q.low_price,
                    "pre_close": q.pre_close,
                    "change": q.change, "change_pct": q.change_pct,
                    "volume": q.volume, "amount": q.amount,
                    "turnover_rate": (q.turnover_rate if q.turnover_rate and q.turnover_rate > 0 else None),
                    "amplitude": q.amplitude,
                    "timestamp": q.timestamp.isoformat() if hasattr(q.timestamp, "isoformat") else str(q.timestamp),
                })
    except Exception as e:
        logger.warning(f"自选股行情获取失败: {e}")

    return {
        "codes": codes,
        "quotes": quotes_data,
        "count": len(quotes_data),
        "timestamp": datetime.now().isoformat(),
        "source": "watchlist",
        "active_data_source": "eastmoney",
    }


@router.get("/quotes/{codes}")
async def batch_quotes(codes: str):
    raw_codes = [c.strip() for c in codes.split(",") if c.strip()]
    return await _fetch_quotes_by_codes(raw_codes, source="explicit")


async def _fetch_quotes_by_codes(raw_codes: list, source: str = "explicit"):
    """
    批量行情查询。

    参数：
    - codes: 逗号分隔的股票代码，如 "000001,600036,000858"
    - 支持代码格式：000001（自动判断市场）、000001.SH、600036.SH、000001.sz 等

    数据源自动降级链路：通达信(主) → 新浪(备1) → 东方财富(备2)
    """
    return await _fetch_quotes_by_codes(raw_codes, source="explicit")


async def _fetch_quotes_by_codes(raw_codes: list, source: str = "explicit"):
    """批量行情查询的核心逻辑"""
    if not raw_codes:
        return {"codes": [], "quotes": [], "count": 0, "timestamp": None, "source": source}

    dsm = _get_dsm()

    # 规范化股票代码格式
    normalized_codes = []
    for code in raw_codes:
        clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        normalized_codes.append(clean)

    quotes_data = []
    errors = []

    try:
        result = await dsm.get_quotes(normalized_codes)
        if result:
            quote_map = {q.code: q for q in result}
            for code in normalized_codes:
                if code in quote_map:
                    q = quote_map[code]
                    quotes_data.append({
                        "code": q.code, "name": q.name,
                        "price": q.price, "open": q.open_price,
                        "high": q.high_price, "low": q.low_price,
                        "pre_close": q.pre_close,
                        "change": q.change, "change_pct": q.change_pct,
                        "volume": q.volume, "amount": q.amount,
                        "turnover_rate": (q.turnover_rate if q.turnover_rate and q.turnover_rate > 0 else None),
                        "amplitude": q.amplitude,
                        "timestamp": q.timestamp.isoformat() if hasattr(q.timestamp, 'isoformat') else str(q.timestamp),
                    })
                else:
                    quotes_data.append({
                        "code": code, "name": None, "price": None,
                        "open": None, "high": None, "low": None,
                        "pre_close": None, "change": None, "change_pct": None,
                        "volume": None, "amount": None,
                        "turnover_rate": None, "amplitude": None,
                        "note": "行情数据暂不可用",
                    })
    except Exception as e:
        logger.error(f"批量获取行情失败: {e}")
        errors.append(str(e))
        for code in normalized_codes:
            try:
                q = await dsm.get_quote(code)
                if q:
                    quotes_data.append({
                        "code": q.code, "name": q.name,
                        "price": q.price, "open": q.open_price,
                        "high": q.high_price, "low": q.low_price,
                        "pre_close": q.pre_close,
                        "change": q.change, "change_pct": q.change_pct,
                        "volume": q.volume, "amount": q.amount,
                        "turnover_rate": (q.turnover_rate if q.turnover_rate and q.turnover_rate > 0 else None),
                        "amplitude": q.amplitude,
                        "timestamp": q.timestamp.isoformat() if hasattr(q.timestamp, 'isoformat') else str(q.timestamp),
                    })
                else:
                    quotes_data.append({"code": code, "name": None, "price": None, "note": "数据获取失败"})
            except Exception as e2:
                logger.warning(f"获取 {code} 行情降级失败: {e2}")
                quotes_data.append({"code": code, "name": None, "price": None, "note": str(e2)})

    # 补充换手率：东财缓存 → akshare 兜底
    await _enrich_turnover_rates(quotes_data)

    try:
        active_source = dsm._active_name if hasattr(dsm, '_active_name') else "unknown"
    except Exception:
        active_source = "unknown"

    return {
        "codes": raw_codes,
        "quotes": quotes_data,
        "count": len(quotes_data),
        "timestamp": datetime.now().isoformat(),
        "active_data_source": active_source,
    }


# 进程内换手率缓存：一旦成功获取就记住，东财API不可用时用缓存值
_turnover_cache: dict = {}

async def _enrich_turnover_rates(quotes_data: list):
    """
    补充换手率：东财缓存优先 → 东财API → 进程缓存兜底。
    只处理 turnover_rate 为 None / 0 的记录。
    """
    global _turnover_cache
    missing = [q for q in quotes_data if q.get("code") and (q.get("turnover_rate") is None or q.get("turnover_rate") == 0)]
    if not missing:
        return

    # 1. 东财缓存
    try:
        from backend.services.eastmoney_enricher import get_enricher
        enricher = get_enricher()
        if enricher._cache:
            for q in missing[:]:
                cd = q["code"]
                enriched = enricher._cache.get(cd, {})
                cached_tr = enriched.get("turnover_rate")
                if cached_tr is not None and cached_tr > 0:
                    q["turnover_rate"] = round(float(cached_tr), 2)
                    missing.remove(q)
    except Exception:
        pass

    if not missing:
        return

    # 2. 东财 push2 API
    try:
        import httpx
        _secids = []
        for q in missing:
            code = q["code"]
            mkt = "1" if code.startswith(("6", "9")) else "0"
            _secids.append(f"{mkt}.{code}")
        async with httpx.AsyncClient(timeout=5) as _c:
            _r = await _c.get("https://push2.eastmoney.com/api/qt/ulist.np/get",
                params={"fltt":"2","invt":"2","fields":"f12,f14,f8","secids":",".join(_secids)},
                headers={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com"})
            _d = _r.json()
            for _item in _d.get("data",{}).get("diff",[]):
                _code = str(_item.get("f12",""))
                _f8 = _item.get("f8")
                if _code and _f8 is not None:
                    _turnover_cache[_code] = round(float(_f8), 2)
                    for q in missing:
                        if q["code"] == _code:
                            q["turnover_rate"] = _turnover_cache[_code]
                            break
    except Exception:
        pass

    if not missing:
        return

    # 3. 进程缓存兜底（东财API不可用时的上次成功值）
    for q in missing[:]:
        cached = _turnover_cache.get(q["code"])
        if cached is not None and cached > 0:
            q["turnover_rate"] = cached
            missing.remove(q)


async def _get_stock_turnover(code: str) -> float:
    """获取单只股票换手率"""
    try:
        dsm = _get_dsm()
        q = await dsm.get_quote(code)
        if q and q.turnover_rate and q.turnover_rate > 0:
            return round(q.turnover_rate, 2)
    except Exception:
        pass
    return 0.0


# ─── K线数据 ─────────────────────────────────────────

@router.get("/kline/{code}")
async def get_kline(
    code: str,
    count: int = Query(120, ge=1, le=1000, description="K线数量"),
    period: str = Query("daily", pattern="^(daily|weekly|monthly|60min|30min|15min|5min|1min)$", description="K线周期"),
):
    """
    获取K线数据。

    参数：
    - code: 股票代码（如 000001, 600036）
    - count: 数据量（默认120，最大1000）
    - period: K线周期（daily/weekly/monthly/60min/30min/15min/5min/1min）

    数据源自动降级链路：通达信(主) → 新浪(备1) → 东方财富(备2)
    """
    dsm = _get_dsm()

    # 规范化代码
    clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

    try:
        kline_data = await dsm.get_kline(clean_code, count)

        klines = []
        for k in kline_data:
            klines.append({
                "code": k.code,
                "date": k.trade_date.strftime("%Y-%m-%d") if hasattr(k.trade_date, 'strftime') else str(k.trade_date),
                "open": k.open_price,
                "close": k.close_price,
                "high": k.high_price,
                "low": k.low_price,
                "volume": k.volume,
                "amount": k.amount,
            })

        try:
            active_source = dsm._active_name if hasattr(dsm, '_active_name') else "unknown"
        except Exception:
            active_source = "unknown"

        return {
            "code": clean_code,
            "period": period,
            "count": len(klines),
            "klines": klines,
            "timestamp": datetime.now().isoformat(),
            "active_data_source": active_source,
        }
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取K线数据失败: {str(e)}")


# ─── 盘前提示（集成AI分析引擎）──────────────────


OVERSEAS_SINA_CODES = {
    "dow_jones":       {"sina": "gb_dji",    "name": "道琼斯", "type": "index"},
    "nasdaq":          {"sina": "gb_ixic",   "name": "纳斯达克", "type": "index"},
    "wti_crude":       {"sina": "hf_CL",     "name": "WTI原油", "type": "future"},
    "brent_crude":     {"sina": "hf_OIL",    "name": "布伦特原油", "type": "future"},
    "gold_futures":    {"sina": "hf_GC",     "name": "黄金期货", "type": "future"},
    "gold_spot":       {"sina": "hf_XAU",    "name": "国际金价", "type": "future_spot"},
}


def _parse_sina_overseas_quote(text: str, data_type: str = "index", name: str = "") -> Optional[Dict[str, Any]]:
    """解析新浪海外指数/期货行情响应"""
    if not text:
        return None
    try:
        parts = text.split('"')
        if len(parts) < 2:
            return None
        values = parts[1].split(",")
        if not values or not values[0]:
            return None
        if data_type == "future":
            # hf_CL/hf_OIL/hf_GC 格式: 最新价,涨跌额,开盘,最高,最低,昨收,时间,前收盘,...
            return {"price": values[0] if values[0] else None,
                    "change": values[1] if len(values) > 1 and values[1] else None,
                    "name": name or "WTI原油"}
        elif data_type == "future_spot":
            # hf_XAU 现货格式: 最新价,昨收,开盘,最高,最低,时间,前收盘,...
            return {"price": values[0] if values[0] else None,
                    "prev_close": values[1] if len(values) > 1 and values[1] else None,
                    "name": name or "国际金价"}
        else:
            # gb_xxx 指数格式: 名称,最新价,涨跌幅%,更新时间,涨跌额,昨收,最高,最低,今开,...
            return {"name": values[0],
                    "price": values[1] if len(values) > 1 and values[1] else None,
                    "change_pct": values[2] if len(values) > 2 and values[2] else None}
    except (ValueError, IndexError):
        return None


async def _collect_overseas_data() -> Dict[str, Any]:
    """
    采集外围市场真实行情数据（美股指数、商品等）。
    通过新浪财经 API 直连获取，不经过 AI 幻觉。
    """
    sina_codes = [info["sina"] for info in OVERSEAS_SINA_CODES.values()]
    url = f"https://hq.sinajs.cn/list={','.join(sina_codes)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }

    result = {}
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"海外行情采集失败: HTTP {resp.status_code}")
                return result
            lines = resp.text.strip().split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                m = re.search(r'var\s+hq_str_(\w+)="(.+)"', line)
                if not m:
                    continue
                var_name = m.group(1)
                for key, info in OVERSEAS_SINA_CODES.items():
                    if info["sina"] == var_name:
                        parsed = _parse_sina_overseas_quote(line, info.get("type", "index"), info.get("name", ""))
                        if parsed:
                            result[key] = parsed
                        break
    except Exception as e:
        logger.warning(f"海外行情采集异常: {e}")

    # 补充汇率数据 (美元/人民币) 和估算美元指数
    try:
        _fx_headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=8, headers=_fx_headers) as fx_cli:
            fx_resp = await fx_cli.get("https://open.er-api.com/v6/latest/USD")
            if fx_resp.status_code == 200:
                fx_data = fx_resp.json()
                rates = fx_data.get("rates", {})
                cny_rate = rates.get("CNY")
                if cny_rate:
                    result["usd_cny"] = {
                        "price": str(cny_rate),
                        "name": "美元/人民币",
                    }
                # 从6种主要货币估算美元指数 DXY
                import math
                eur = rates.get("EUR")
                jpy = rates.get("JPY")
                gbp = rates.get("GBP")
                cad = rates.get("CAD")
                sek = rates.get("SEK")
                chf = rates.get("CHF")
                if all(v is not None for v in [eur, jpy, gbp, cad, sek, chf]):
                    eurusd = 1.0 / eur
                    gbpusd = 1.0 / gbp
                    dxy = 50.14348112 * math.pow(eurusd, -0.576) * math.pow(jpy, 0.136) * math.pow(gbpusd, -0.119) * math.pow(cad, 0.091) * math.pow(sek, 0.042) * math.pow(chf, 0.036)
                    result["dxy"] = {
                        "price": f"{dxy:.2f}",
                        "name": "美元指数",
                    }
    except Exception as e:
        logger.warning(f"汇率/DXY采集失败: {e}")

    return result


async def _call_premarket_analysis(market_data: Dict, overseas_section: str = None) -> Dict:
    """调用AI分析引擎生成盘前提示（外围市场小节由Python填入真实数据）"""
    try:
        from backend.services.analysis_engine import LLMClient

        # 读取当前默认模板
        template_content = _read_default_template()
        if not template_content:
            template_content = "A股盘前提示模板（包含五大板块：外围市场、重要消息、指数预判、热点方向、操作策略）"

        # 构建 AI 提示：外围市场小节已由Python预填充，AI只写二到五
        if overseas_section:
            section_hint = f"""
【重要】「外围市场概况」已由系统使用真实数据填充如下，你**必须原样保留**这段内容，
不得修改其中的任何数字或文字。此段已作为最终输出的一、部分。

{overseas_section}

请直接从「二、重要消息与政策」开始输出，不要重复输出一、部分。
"""
        else:
            section_hint = ""

        system_prompt = f"""你是专业的A股盘前分析助手。

{section_hint}

用户提供了一份盘前提示模板，请基于你的知识填充以下内容。

格式要求：
- 先输出「二、重要消息与政策」，再依次输出「三、指数技术面预判」「四、热点方向跟踪」「五、操作策略建议」
- 保留模板标题（二、到五、）不变
- 不要使用Markdown标记符号
- 每个字段一行，用简洁的段落文字描述
- 使用【】保留分类标记如【主线】【风险】
- 整体风格：简洁、清晰、易读

A股指数参考数据：
```json
{json.dumps(market_data.get("indices", []), ensure_ascii=False, default=str)}
```
"""

        client = LLMClient()
        result = await client.chat(
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.3,
            max_tokens=4096,
            search=False,
        )
        return result
    except Exception as e:
        logger.error(f"AI盘前提示生成失败: {e}")
        return {"success": False, "error": str(e)}


def _build_overseas_section(overseas: Dict) -> str:
    """
    用Python将外围市场真实数据填入「外围市场概况」小节，
    返回不可由AI修改的固定文本。
    """
    lines = []
    lines.append("一、外围市场概况（影响A股开盘情绪，重点跟踪核心指标）")

    # ── 美股 ──
    dj = overseas.get("dow_jones", {})
    nq = overseas.get("nasdaq", {})
    dow_pct = dj.get("change_pct")
    nas_pct = nq.get("change_pct")
    if dow_pct is not None and dow_pct != "":
        dow_dir = "上涨" if float(dow_pct) >= 0 else "下跌"
        dow_line = f"美股：道指隔夜收盘{dow_dir}{abs(float(dow_pct)):.2f}%"
    else:
        dow_line = "美股：道指隔夜收盘【待补充】"
    if nas_pct is not None and nas_pct != "":
        nas_dir = "上涨" if float(nas_pct) >= 0 else "下跌"
        nas_line = f"，纳指隔夜收盘{nas_dir}{abs(float(nas_pct)):.2f}%"
    else:
        nas_line = "，纳指隔夜收盘【待补充】"
    lines.append(dow_line + nas_line + "（备注：具体板块表现详见下文分析）；")

    # ── A50（暂无直接数据源，用沪深300近似替代）──
    indices_300 = overseas.get("csi300", {}).get("price") or overseas.get("沪深300", {}).get("change_pct")
    lines.append("富时中国A50指数（隔夜）：【待补充，参考沪深300走势】（反映外资对A股的预判）；")

    # ── 汇率 ──
    fx = overseas.get("usd_cny", {})
    fx_price = fx.get("price")
    dxy = overseas.get("dxy", {}).get("price")
    if fx_price and dxy:
        lines.append(f"美元指数：{dxy}，走势【偏强】；人民币兑美元中间价：{fx_price}，汇率【偏弱】（影响北向资金流向及出口型企业）；")
    elif fx_price:
        lines.append(f"美元指数：【待补充】；人民币兑美元中间价：{fx_price}，汇率【偏弱】（影响北向资金流向及出口型企业）；")
    else:
        lines.append("美元指数：【待补充】；人民币兑美元中间价：【待补充】，汇率【待补充】（影响北向资金流向及出口型企业）；")

    # ── 大宗商品 ──
    items = []
    wti_price = overseas.get("wti_crude", {}).get("price")
    brent_price = overseas.get("brent_crude", {}).get("price")
    gold_f_price = overseas.get("gold_futures", {}).get("price")
    gold_s_price = overseas.get("gold_spot", {}).get("price")
    if wti_price:
        items.append(f"WTI原油{wti_price}美元/桶")
    if brent_price:
        items.append(f"布伦特原油{brent_price}美元/桶")
    if gold_f_price:
        items.append(f"黄金期货{gold_f_price}元/克")
    if gold_s_price:
        items.append(f"国际金价{gold_s_price}美元/盎司")
    if items:
        lines.append("大宗商品：" + "、".join(items) + "（关联A股对应产业链板块）；")
    else:
        lines.append("大宗商品：原油（WTI）【待补充】、黄金【待补充】、有色（铜/铝等）整体偏【待补充】（关联A股对应产业链板块）；")

    return "\n".join(lines)


def _read_default_template() -> str:
    """读取默认盘前提示模板文件（优先使用用户设置的默认模板）"""
    try:
        from backend.api.config_api import resolve_template_path
        path = resolve_template_path("premarket")
    except Exception:
        path = None
    if not path:
        path = os.path.join("data", "templates", "A股市场盘前提示模板.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"默认模板文件不存在: {path}")
        return ""


def _fill_template(template_text: str, indices_data: list, today: str, weekday_cn: str,
                   extra: dict = None, nb_flow: dict = None, limit_str: str = "", news_str: str = "") -> str:
    """
    用实时数据填充模板中的所有类型占位符。
    """
    if extra is None: extra = {}
    if nb_flow is None: nb_flow = {"today": "", "cum5": ""}
    result = template_text

    # ── 1. 日期 ──
    date_str = today.replace("-", " 年 ", 1).replace("-", " 月 ", 1) + " 日"
    result = result.replace("XXXX 年 XX 月 XX 日", date_str)
    result = result.replace("星期 X", weekday_cn)

    # ── 2. 提取指数数据 ──
    idx_data = {}  # name -> {price, chg, arrow, code}
    for i in indices_data:
        code = str(i.get("code", ""))
        price = i.get("price", 0) or 0
        chg = i.get("change_pct", 0) or 0
        name = (i.get("name") or "").replace(".SH", "").replace(".SZ", "")
        arrow = "↑" if chg > 0 else ("↓" if chg < 0 else "→")
        idx_data[code] = {"price": price, "chg": chg, "arrow": arrow, "name": name}

    sh = idx_data.get("000001") or idx_data.get("000001.SH") or {}
    cy = idx_data.get("399006") or idx_data.get("399006.SZ") or {}
    hs300 = idx_data.get("000300") or idx_data.get("000300.SH") or {}

    # ── 3. 核心变量 ──
    sh_chg = sh.get("chg", 0)
    cy_chg = cy.get("chg", 0)
    sh_price = sh.get("price", 0)
    cy_price = cy.get("price", 0)
    market_up = sh_chg > 0
    market_down = sh_chg < 0
    market_flat = abs(sh_chg) < 0.3

    # ── 4. 特定替换（先做，保留___供后续通用替换使用）──
    us_val = extra.get("us", "")
    if us_val:
        result = re.sub(r"美股：[^\n]*", f"美股：{us_val}", result)
    fx_val = extra.get("fx", "")
    if fx_val:
        result = result.replace("___（具体点位，如98.70）", f"{fx_val}（实时）")
        result = result.replace("___（具体点位，如6.88）", f"{fx_val.split()[-1]}（实时）")
    comm_val = extra.get("commodity", "")
    if comm_val:
        result = re.sub(r"大宗商品：[^\n]*", f"大宗商品：{comm_val}（实时）", result)
    to_val = extra.get("turnover", "")
    if to_val:
        result = re.sub(r"两市成交额[^（]*", f"两市成交额{to_val.replace('两市成交额约','')}", result)
    if nb_flow.get("today"):
        result = re.sub(r"北向资金昨日流向：[^\n]*", nb_flow["today"], result)
        if nb_flow.get("cum5"):
            result = re.sub(r"近5日累计流向[^，]*", nb_flow["cum5"], result)
    if limit_str:
        result = re.sub(r"昨日涨停家数[^，]*", f"昨日涨停家数{limit_str}", result)
    if news_str:
        # 同时匹配 ___ 和 待补充（用户可能编辑了模板）
        result = re.sub(r"宏观政策：(___|待补充[^）]*）", f"宏观政策：{news_str[:80]}", result)
        result = re.sub(r"行业利好：(___|待补充[^）]*）", f"行业利好：{news_str[40:120]}", result)
        result = re.sub(r"行业利空：(___|待补充[^）]*）", f"行业利空：{news_str[80:160]}", result)

    # ── 5. 上证、创业板支撑压力 ──
    if sh:
        p, a, chg = sh["price"], sh["arrow"], sh["chg"]
        result = re.sub(
            r"上证指数：关键支撑[^，]*，关键压力[^；]*；?",
            f"上证指数：关键支撑{p*0.98:.0f}点（实时{p:.2f} {a}{abs(chg):.2f}%），关键压力{p*1.02:.0f}点；",
            result)
    if cy:
        p, a = cy["price"], cy["arrow"]
        result = re.sub(
            r"创业板指：关键支撑[^，]*，关键压力[^；]*；?",
            f"创业板指：关键支撑{p*0.98:.0f}点，关键压力{p*1.02:.0f}点；",
            result)

    # ── 6. 通用替换表（最后执行，不破坏上方特定替换）──
    # 同时匹配 ___ 和 待补充（用户可能编辑模板把___改成了"待补充"）
    _plh = r"(?:___|待补充)"  # placeholder: ___ or 待补充
    general_repl = [
        (r"↑↓___%", f"{'↑' if sh_chg > 0 else '↓'}{abs(sh_chg):.2f}%" if sh else "--%"),
        (r"支撑___点", f"支撑{sh_price*0.98:.0f}点" if sh else "支撑待定"),
        (r"压力___点", f"压力{sh_price*1.02:.0f}点" if sh else "压力待定"),
        (_plh + r"家", "--家"),
        (_plh + r"%", "--"),
        (_plh + r"成", "5-7成"),
        (r"___+", "--"),
        (r"待补充[^（\n]*（[^）]*）", r"\g<0>"),  # 保留带括号说明的待补充（显示原样）
        (r"【利好/中性/利空】", "【利好】" if sh_chg > 0 else "【中性】" if sh_chg >= -0.3 else "【利空】"),
        (r"【偏强/偏弱】", "【偏强】" if sh_chg > 0 else "【偏弱】"),
        (r"【强/一般/弱】", "【强】" if sh_chg > 0.5 else "【一般】" if sh_chg >= -0.5 else "【弱】"),
        (r"【高开震荡/低开修复/区间整理/低开低走】",
         "【高开震荡】" if sh_chg > 0 else "【低开修复】" if sh_chg > -0.5 else "【区间整理】"),
        (r"【低吸为主（依托关键支撑位）/ 谨慎控仓（规避节前避险情绪）/ 快进快出（短线博弈轮动行情）】",
         "【低吸为主】" if sh_chg > 0 else "【谨慎控仓】"),
        (r"【多看少动（等待明确信号）/ 分批低吸（逢支撑位布局，不一次性满仓）/ 不追高（规避高位题材回调风险）/ 逢高减仓（节前落袋为安）】",
         "【分批低吸】"),
        (r"【[^】]*/[^】]*】", "【--】"),
    ]

    for pattern, replacement in general_repl:
        result = re.sub(pattern, replacement, result)

    # ── 5. 具体替换 ──
    # 上证、创业板支撑压力
    if sh:
        p = sh["price"]
        a = sh["arrow"]
        chg = sh["chg"]
        result = re.sub(
            r"上证指数：关键支撑[^，]*，关键压力[^；]*；?",
            f"上证指数：关键支撑{p*0.98:.0f}点（实时{p:.2f} {a}{abs(chg):.2f}%），关键压力{p*1.02:.0f}点；",
            result)
    if cy:
        p = cy["price"]
        a = cy["arrow"]
        result = re.sub(
            r"创业板指：关键支撑[^，]*，关键压力[^；]*；?",
            f"创业板指：关键支撑{p*0.98:.0f}点，关键压力{p*1.02:.0f}点；",
            result)

    # ── 6. 填入外围市场、汇率、商品、成交额、北向资金、涨跌停、新闻 ──
    # （在通用___替换之前执行，避免___已被替换为"待补充"）
    us_val = extra.get("us", "")
    if us_val:
        result = re.sub(r"美股：[^\n]*", f"美股：{us_val}", result)
    fx_val = extra.get("fx", "")
    if fx_val:
        # 替换美元指数和人民币的___占位
        result = result.replace("___（具体点位，如98.70）", f"{fx_val}（实时）")
        result = result.replace("___（具体点位，如6.88）", f"{fx_val.split()[-1]}（实时）")
    comm_val = extra.get("commodity", "")
    if comm_val:
        result = re.sub(r"大宗商品：[^\n]*", f"大宗商品：{comm_val}（实时）", result)
    to_val = extra.get("turnover", "")
    if to_val:
        result = re.sub(r"两市成交额[^（]*", f"两市成交额{to_val.replace('两市成交额约','')}", result)
    if nb_flow.get("today"):
        result = re.sub(r"北向资金昨日流向：[^\n]*", nb_flow["today"], result)
        if nb_flow.get("cum5"):
            result = re.sub(r"近5日累计流向[^，]*", nb_flow["cum5"], result)
    if limit_str:
        result = re.sub(r"昨日涨停家数[^，]*", f"昨日涨停家数{limit_str}", result)
    if news_str:
        result = result.replace("宏观政策：___", f"宏观政策：{news_str[:80]}")
        result = result.replace("行业利好：___", f"行业利好：{news_str[40:120]}")

    return result


async def _build_premarket_tip(indices_data: list, generated_at: str, is_ai: bool, ai_content: str = None, overseas_section: str = None) -> dict:
    """
    从系统设置中的默认盘前提示模板文件读取结构，填充实时数据后生成盘前提示。
    五大板块：外围市场、重要消息、指数预判、热点方向、操作策略。
    自动从东方财富获取板块涨跌和北向资金数据。
    
    overseas_section: 由 Python 预填充的外围市场数据块（AI模式下前置）
    """
    today = datetime.now().strftime("%Y-%m-%d")
    weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][datetime.now().weekday()]

    if is_ai and ai_content:
        # 清理AI输出中的markdown符号
        cleaned = ai_content
        # 去掉 markdown 加粗 **text** → text
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)
        # 去掉 markdown 斜杠 *text* → text（但保留【】中的★☆等装饰）
        cleaned = re.sub(r'^\s*\*+\s*', '', cleaned, flags=re.MULTILINE)
        # 去掉 ↑↓ 等多余箭头（保留在数字前的，去掉单独的）
        cleaned = re.sub(r'↑↓', '', cleaned)
        # 去掉行首的 -  和 •  前缀
        cleaned = re.sub(r'^[\s]*[-•·]\s*', '', cleaned, flags=re.MULTILINE)
        # 多个空行合并
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 按一、二、三、四、五拆分
        ai_sections = []
        ai_titles = ["外围市场概况","重要消息与政策","指数技术面预判","热点方向跟踪","操作策略建议"]
        ai_labels = ["一、","二、","三、","四、","五、"]
        lines = cleaned.strip().split("\n")
        ci, cl = -1, []
        for line in lines:
            m = False
            for si, lb in enumerate(ai_labels):
                if lb in line:
                    if ci >= 0 and cl:
                        ai_sections.append({"title": ai_titles[ci], "content": "\n".join(cl).strip()})
                    ci, cl, m = si, [], True
                    break
            if not m and ci >= 0:
                cl.append(line)
        if ci >= 0 and cl:
            ai_sections.append({"title": ai_titles[ci], "content": "\n".join(cl).strip()})
        if not ai_sections:
            ai_sections = [{"title": "AI盘前提示", "content": cleaned.strip()}]
        # 如果提供了预填充的外围市场数据，前置为第一段
        if overseas_section:
            ai_sections.insert(0, {"title": "外围市场概况", "content": overseas_section})
        return {"date": today, "marketPrediction": cleaned.strip(), "keyLevels": "",
            "sectorRecommendations": [], "riskTips": [], "updatedAt": generated_at,
            "dataSource": "AI", "generatedAt": generated_at, "sections": ai_sections}

    # ====== 并行获取所有额外数据 ======
    news_task = _fetch_top_news()
    sectors_task = _fetch_sector_performance()
    nb_task = _fetch_northbound_flow()
    extra_task = _fetch_market_overview_extra()
    limit_task = _fetch_limit_up_down()
    results = await asyncio.gather(
        asyncio.wait_for(news_task, timeout=5),
        asyncio.wait_for(sectors_task, timeout=5),
        asyncio.wait_for(nb_task, timeout=5),
        asyncio.wait_for(extra_task, timeout=5),
        asyncio.wait_for(limit_task, timeout=5),
        return_exceptions=True)
    news_str = results[0] if not isinstance(results[0], Exception) else ""
    sectors = results[1] if not isinstance(results[1], Exception) else {"leaders":[],"laggards":[]}
    nb_flow = results[2] if not isinstance(results[2], Exception) else {"today":"","cum5":""}
    extra = results[3] if not isinstance(results[3], Exception) else {"us":"","fx":"","commodity":"","turnover":""}
    limit_str = results[4] if not isinstance(results[4], Exception) else ""

    # ====== 从模板文件读取结构 ======
    template_text = _read_default_template()
    if template_text:
        filled = _fill_template(template_text, indices_data, today, weekday_cn,
                               extra=extra, nb_flow=nb_flow, limit_str=limit_str, news_str=news_str)
        # 在热点方向板块插入实时板块数据
        sec_text = ""
        if sectors.get("leaders"):
            sec_text += "▶ 领涨：" + "、".join([s["name"] for s in sectors["leaders"]]) + "\n"
        if sectors.get("laggards"):
            sec_text += "▼ 领跌：" + "、".join([s["name"] for s in sectors["laggards"]]) + "\n"
        if sec_text and "今日重点关注方向" in filled:
            filled = filled.replace("今日重点关注方向：", f"今日重点关注方向：\n{sec_text}", 1)
    else:
        filled = f"【{today} {weekday_cn} 盘前展望】\n暂无模板文件，请在系统配置中设置默认模板。"

    # ====== 将填充后的模板按板块拆分为结构化 sections ======
    section_titles = ["外围市场概况", "重要消息与政策", "指数技术面预判", "热点方向跟踪", "操作策略建议"]
    section_labels = ["一、", "二、", "三、", "四、", "五、"]

    sections = []
    lines = filled.split("\n")
    current_idx = -1
    current_lines = []

    for line in lines:
        matched = False
        for si, label in enumerate(section_labels):
            if label in line:
                # 保存上一个板块
                if current_idx >= 0 and current_lines:
                    sections.append({
                        "title": section_titles[current_idx],
                        "content": "\n".join(current_lines).strip()
                    })
                current_idx = si
                current_lines = []
                matched = True
                break
        if not matched:
            if current_idx >= 0:
                current_lines.append(line)

    # 最后一个板块
    if current_idx >= 0 and current_lines:
        sections.append({
            "title": section_titles[current_idx],
            "content": "\n".join(current_lines).strip()
        })

    # 指数行情摘要（用于 marketPrediction 字段）
    index_lines = []
    for i in indices_data:
        chg = i.get("change_pct")
        arrow = "↑" if chg and chg > 0 else ("↓" if chg and chg < 0 else "→")
        idx_name = (i.get("name") or "?").replace(".SH","").replace(".SZ","")
        index_lines.append(f"{idx_name} {i.get('price',0):.2f} {arrow}{abs(chg or 0):.2f}%")

    # 从模板 sections 提取关注板块和风险提示
    recs = []
    risks = []
    for s in sections:
        if "热点" in s["title"] and "主线" in s["content"]:
            for line in s["content"].split("\n"):
                line = line.strip()
                if line.startswith("【主线】") or line.startswith("【轮动】"):
                    recs.append(line.replace("【主线】", "").replace("【轮动】", "").strip())
        if "操作策略" in s["title"] or "风险" in s["title"]:
            for line in s["content"].split("\n"):
                line = line.strip()
                if line.startswith("风险"):
                    risks.append(line.replace("风险点：", "").replace("风险", "").strip())

    return {
        "date": today,
        "marketPrediction": filled,
        "keyLevels": "",
        "sectorRecommendations": recs if recs else ["请查看盘前提示详情"],
        "riskTips": risks if risks else ["市场有风险，投资需谨慎"],
        "updatedAt": generated_at,
        "dataSource": "基础行情",
        "generatedAt": generated_at,
        "sections": sections,
    }


# AkShare缓存（后台预热 + 长缓存，避免阻塞请求）
_akshare_data = {"spot_df": None, "sector_df": None, "nb_df": None, "ts": 0}
_AK_CACHE_SEC = 300  # 缓存5分钟


def _ak_load_spot():
    import akshare as ak
    return ak.stock_zh_a_spot()


async def _get_akshare_spot():
    """获取全市场行情（AkShare, 线程池+缓存）"""
    import time
    now = time.time()
    if _akshare_data["spot_df"] is not None and now - _akshare_data["ts"] < _AK_CACHE_SEC:
        return _akshare_data["spot_df"]
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, _ak_load_spot)
    _akshare_data["spot_df"] = df
    _akshare_data["ts"] = now
    return df


async def _warm_akshare():
    """后台预热缓存（启动时异步执行）"""
    logger.info("AkShare后台预热开始...")
    import time
    loop = asyncio.get_event_loop()
    try:
        df = await loop.run_in_executor(None, _ak_load_spot)
        _akshare_data["spot_df"] = df
        _akshare_data["ts"] = time.time()
        logger.info(f"AkShare缓存就绪：{len(df)}只股票")
    except Exception as e:
        logger.warning(f"AkShare预热失败: {e}")


async def _fetch_sector_performance() -> dict:
    """板块涨跌（通过模块数据源映射获取）"""
    dsm = _get_dsm()
    try:
        source = dsm.get_active_for_module("market_sector")
        if source.name in ("akshare_em", "akshare"):
            try:
                import akshare as ak
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, ak.stock_board_industry_spot_em)
                if df is not None and not df.empty:
                    leaders, laggards = [], []
                    for _, r in df.head(8).iterrows():
                        n = str(r.get('板块名称',''))
                        c = r.get('涨跌幅')
                        if n and c is not None:
                            (leaders if float(c)>0 else laggards).append({"name":n, "chg":round(float(c),2)})
                    return {"leaders": leaders[:5], "laggards": laggards[:3]}
            except Exception as e:
                logger.warning(f"板块-akshare_em 失败: {e}")
        elif source.name == "eastmoney":
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as c:
                    url = "https://push2.eastmoney.com/api/qt/clist/get"
                    params = {
                        "pn": "1", "pz": "20", "po": "1", "np": "1",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                        "fltt": "2", "invt": "2", "fid": "f3",
                        "fs": "m:90+t:2",
                        "fields": "f12,f14,f3",
                    }
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
                    resp = await c.get(url, params=params, headers=headers)
                    data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", [])
                    if items:
                        leaders, laggards = [], []
                        for it in items[:8]:
                            n = str(it.get("f14", ""))
                            c = it.get("f3")
                            if n and c is not None:
                                (leaders if float(c) > 0 else laggards).append({"name": n, "chg": round(float(c), 2)})
                        return {"leaders": leaders[:5], "laggards": laggards[:3]}
            except Exception as e:
                logger.warning(f"板块-eastmoney 失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"板块数据源不可用: {e}")
    return {"leaders":[], "laggards":[]}


async def _fetch_northbound_flow() -> dict:
    """北向资金（通过模块数据源映射获取）"""
    dsm = _get_dsm()
    try:
        source = dsm.get_active_for_module("market_northbound")
        if source.name == "akshare":
            try:
                import akshare as ak
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, lambda: ak.stock_hsgt_hist_em())
                if df is not None and not df.empty:
                    last = df.iloc[-1]
                    total = float(last.get('当日成交净买入',0))
                    d = "净流入" if total>0 else "净流出"
                    today = f"北向资金{d}{abs(total):.0f}亿"
                    total5 = df.tail(5)['当日成交净买入'].sum()
                    d5 = "净流入" if total5>0 else "净流出"
                    return {"today": today, "cum5": f"近5日累计{d5}{abs(total5):.0f}亿"}
            except Exception as e:
                logger.warning(f"北向资金获取失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"北向资金数据源不可用: {e}")
    return {"today":"", "cum5":""}


async def _fetch_limit_up_down() -> str:
    """涨跌停家数（通过模块数据源映射获取）"""
    dsm = _get_dsm()
    try:
        source = dsm.get_active_for_module("market_limit")
        if source.name in ("akshare", "akshare_em"):
            # AkShare：从缓存或实时请求计算
            try:
                df = _akshare_data.get("spot_df")
                if df is not None and not df.empty and '涨跌幅' in df.columns:
                    up = len(df[df['涨跌幅']>=9.8])
                    down = len(df[df['涨跌幅']<=-9.8])
                    return f"涨停{up}家，跌停{down}家"
            except Exception as e:
                logger.warning(f"涨跌停-AkShare缓存失败: {e}")
        elif source.name == "eastmoney":
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as c:
                    url = "https://push2.eastmoney.com/api/qt/clist/get"
                    params = {
                        "pn": "1", "pz": "5000", "po": "0", "np": "1",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                        "fltt": "2", "invt": "2", "fid": "f3",
                        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2",
                        "fields": "f12,f3",
                    }
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
                    resp = await c.get(url, params=params, headers=headers)
                    data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", [])
                    if items:
                        up = sum(1 for it in items if it.get("f3") is not None and float(it["f3"]) >= 9.8)
                        down = sum(1 for it in items if it.get("f3") is not None and float(it["f3"]) <= -9.8)
                        return f"涨停{up}家，跌停{down}家"
            except Exception as e:
                logger.warning(f"涨跌停-eastmoney失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"涨跌停数据源不可用: {e}")
    # 降级：同花顺爬虫
    result = await _fetch_10jqka_limit()
    if result:
        return result
    return ""


async def _fetch_market_turnover() -> str:
    """成交额（AkShare缓存优先，同花顺降级）"""
    try:
        df = _akshare_data.get("spot_df")
        if df is not None and not df.empty and '成交额' in df.columns:
            total = df['成交额'].sum() / 1e8
            return f"两市成交额约{total:.0f}亿元"
    except Exception as e:
        logger.warning(f"成交额缓存取失败: {e}")
    return ""


# ─── 同花顺网页爬虫（无限制备用数据源）────────────────


async def _fetch_10jqka_json(url: str) -> dict:
    """请求同花顺页面并解析JSON"""
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as c:
            r = await c.get(url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            # 尝试多种解析
            text = r.text
            import json as j
            # 搜索JSON数据
            import re as r2
            for pat in [r'"data":\{.*?"items":\[.*?\]', r'"items":\[.*?\]', r'\[\{.*?\}\]']:
                m = r2.search(text, r2.DOTALL)
                if m:
                    try:
                        return j.loads('{' + m.group() + '}')
                    except:
                        pass
            return {}
    except Exception as e:
        logger.warning(f"同花顺爬取失败: {e}")
        return {}


async def _fetch_10jqka_limit() -> str:
    """从同花顺数据中心爬取涨停/跌停数据"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0, verify=False) as c:
            r = await c.get("https://data.10jqka.com.cn/market/",
                headers={"User-Agent":"Mozilla/5.0"})
            text = r.text
            up_m = re.search(r'涨停.*?(\d+)', text)
            down_m = re.search(r'跌停.*?(\d+)', text)
            up = up_m.group(1) if up_m else "?"
            down = down_m.group(1) if down_m else "?"
            return f"涨停{up}家，跌停{down}家"
    except Exception as e:
        logger.warning(f"同花顺涨跌停失败: {e}")
        return ""


async def _fetch_top_news() -> str:
    """从同花顺财经爬取热点新闻标题"""
    import httpx
    sources = [
        ("https://finance.10jqka.com.cn/", r'<span class="tit">([^<]+)</span>'),
        ("https://www.cls.cn/telegraph", r'"title":"([^"]+)"'),
        ("https://finance.sina.com.cn/", r'<a[^>]*href="[^"]*"[^>]*>([^<]{10,50})</a>'),
    ]
    all_titles = []
    for url, pattern in sources:
        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as c:
                r = await c.get(url, headers={"User-Agent":"Mozilla/5.0"})
                text = r.text
                titles = re.findall(pattern, text)
                # 过滤非中文标题
                titles = [t.strip() for t in titles if t.strip() and len(t.strip()) > 8][:3]
                all_titles.extend(titles)
                if len(all_titles) >= 5:
                    break
        except Exception as e:
            logger.warning(f"新闻源失败 {url}: {e}")
            continue
    if all_titles:
        return "；".join(all_titles[:5])
    return ""


async def _fetch_market_overview_extra() -> dict:
    """外围市场/商品/汇率（通过模块数据源映射获取）"""
    result = {"us":"", "fx":"", "commodity":"", "turnover":""}
    
    dsm = _get_dsm()
    try:
        source = dsm.get_active_for_module("market_overseas")
        if source.name == "sina":
            sina_codes = "gb_$dji,gb_ixic,gb_$inx,hf_CL,hf_GC,hf_SI,hg_COPPER,fx_susdcny,fx_susdcnh"
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    r = await c.get(f"https://hq.sinajs.cn/list={sina_codes}",
                        headers={"Referer":"https://finance.sina.com.cn"})
                    text = r.content.decode("gbk", errors="ignore")
                    for line in text.split(";\n"):
                        if not line.strip(): continue
                        val = ""
                        if 'gb_"' in line and line.count('"') >= 2:
                            parts = line.split('"')[1].split(",")
                            n = {"$dji":"道指","ixic":"纳指","$inx":"标普500"}.get(line[line.rfind("gb_")+3:line.rfind("=")].strip('"').lower(), "")
                            if len(parts) >= 4 and n:
                                val = f"{n} {float(parts[1]):.0f} {'↑' if float(parts[2])>0 else '↓'}{abs(float(parts[2])):.2f}%"
                        elif 'hf_' in line and line.count('"') >= 2:
                            parts = line.split('"')[1].split(",")
                            s = line[line.rfind("hf_")+3:line.rfind("=")].strip('"')
                            names = {"CL":"WTI原油","GC":"黄金","SI":"白银","COPPER":"铜"}
                            n = names.get(s,"")
                            if len(parts) >= 2 and n:
                                val = f"{n} {parts[0]}美元"
                        elif 'fx_' in line and line.count('"') >= 2:
                            parts = line.split('"')[1].split(",")
                            if len(parts) >= 2:
                                val = f"美元/人民币 {parts[1]}"
                        if val and not result.get("us") and ("道指" in val or "标普" in val):
                            result["us"] = (result.get("us","") + " | " if result["us"] else "") + val
                        elif val and ("原油" in val or "黄金" in val):
                            result["commodity"] = (result.get("commodity","") + " | " if result["commodity"] else "") + val
                        elif val and "人民币" in val:
                            result["fx"] = val
            except Exception as e:
                logger.warning(f"新浪外围数据失败: {e}")
        elif source.name == "eastmoney":
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as c:
                    # 东方财富全球指数行情
                    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
                    params = {
                        "fltt": "2", "fields": "f2,f3,f4,f12,f14",
                        "secids": "1.000001,0.9984,0.9985,1.000300",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    }
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
                    resp = await c.get(url, params=params, headers=headers)
                    data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", [])
                    us_parts = []
                    for it in items:
                        nm = str(it.get("f14", ""))
                        pr = it.get("f2")
                        chg = it.get("f3")
                        if nm and pr is not None and chg is not None:
                            arrow = "↑" if chg > 0 else "↓"
                            us_parts.append(f"{nm} {pr:.0f} {arrow}{abs(chg):.2f}%")
                    if us_parts:
                        result["us"] = " | ".join(us_parts)
            except Exception as e:
                logger.warning(f"东财外围数据失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"外围市场数据源不可用: {e}")
    
    # 成交额从全市场行情计算
    turnover = await _fetch_market_turnover()
    if turnover:
        result["turnover"] = turnover
    return result


async def _collect_indices() -> list:
    """获取主要指数行情数据"""
    dsm = _get_dsm()
    indices_data = []
    for code in ["000001.SH", "399001.SZ", "399006.SZ", "000300.SH", "000688.SH"]:
        try:
            q = await dsm.get_quote(code)
            if q:
                indices_data.append({
                    "code": q.code,
                    "name": q.name,
                    "price": q.price,
                    "change_pct": q.change_pct,
                })
        except Exception:
            pass
    return indices_data


PRE_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "premarket_cache")
os.makedirs(PRE_CACHE_DIR, exist_ok=True)


def _load_cached_premarket() -> Optional[dict]:
    """读取今日盘前提示缓存"""
    today = datetime.now().strftime("%Y-%m-%d")
    cache_file = os.path.join(PRE_CACHE_DIR, f"premarket_{today}.json")
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"盘前提示缓存读取失败: {e}")
    return None


def _save_premarket_cache(tip: dict):
    """保存盘前提示到今日缓存"""
    today = datetime.now().strftime("%Y-%m-%d")
    cache_file = os.path.join(PRE_CACHE_DIR, f"premarket_{today}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(tip, f, ensure_ascii=False, default=str)
        logger.info(f"盘前提示已缓存: {cache_file}")
    except Exception as e:
        logger.warning(f"盘前提示缓存写入失败: {e}")


@router.get("/premarket")
async def premarket_overview():
    """
    盘前提示概览。
    交易日每天自动生成一次并缓存，其余时间读取缓存。
    手动点击重新生成会覆盖今日缓存。
    """
    now = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")

    # 检查今日缓存
    cached = _load_cached_premarket()
    if cached:
        return {
            "tip": cached,
            "is_ai_generated": cached.get("_ai", False),
            "generated_at": cached.get("generatedAt", now),
            "source": "cache",
        }

    # 首次访问今日才生成
    indices_data = await _collect_indices()
    overseas_data = await _collect_overseas_data()
    overseas_section = _build_overseas_section(overseas_data)
    ai_result = await _call_premarket_analysis({
        "indices": [{"source": "权威数据", **i} for i in indices_data],
        "timestamp": now,
    }, overseas_section=overseas_section)

    try:
        if ai_result.get("success"):
            tip = await _build_premarket_tip(indices_data, now, is_ai=True, ai_content=ai_result["content"], overseas_section=overseas_section)
            tip["_ai"] = True
        else:
            tip = await _build_premarket_tip(indices_data, now, is_ai=False, overseas_section=overseas_section)
            tip["_ai"] = False
        _save_premarket_cache(tip)
    except Exception as e:
        logger.error(f"盘前提示生成失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        tip = {"date": today, "marketPrediction": f"盘前提示生成失败: {e}",
               "keyLevels": "", "sectorRecommendations": [], "riskTips": [],
               "updatedAt": now, "dataSource": "error", "generatedAt": now, "sections": []}

    return {
        "tip": tip,
        "is_ai_generated": tip.get("_ai", False),
        "generated_at": now,
        "source": "ai" if tip.get("_ai") else "fallback",
    }


@router.post("/premarket/generate")
async def generate_premarket():
    """
    生成盘前提示。
    调用AI分析引擎生成，保存到今日缓存。
    """
    indices_data = await _collect_indices()
    now = datetime.now().isoformat()
    overseas_data = await _collect_overseas_data()
    overseas_section = _build_overseas_section(overseas_data)

    ai_result = await _call_premarket_analysis({
        "indices": [{"source": "权威数据", **i} for i in indices_data],
        "timestamp": now,
    }, overseas_section=overseas_section)

    if ai_result.get("success"):
        tip = await _build_premarket_tip(indices_data, now, is_ai=True, ai_content=ai_result["content"], overseas_section=overseas_section)
    else:
        tip = await _build_premarket_tip(indices_data, now, is_ai=False, overseas_section=overseas_section)

    tip["_ai"] = ai_result.get("success", False)
    _save_premarket_cache(tip)  # 覆盖今日缓存

    return {
        "status": "ok",
        "message": "盘前提示生成成功" if ai_result.get("success") else "盘前提示（降级模式）",
        "tip": tip,
        "is_ai_generated": ai_result.get("success", False),
        "generated_at": now,
        "source": "ai" if ai_result.get("success") else "fallback",
    }


# ─── 交易日判断 ────────────────────────────────────────

@router.get("/is-trading-day")
async def is_trading_day():
    """判断今天是否为A股交易日，同时返回当前时段和距下次开盘时间（使用北京时间）"""
    from zoneinfo import ZoneInfo
    _tz = ZoneInfo("Asia/Shanghai")
    now = datetime.now(_tz)
    today = now.strftime("%Y-%m-%d")
    dow = now.weekday()  # 0=Mon
    h, m = now.hour, now.minute
    t = h * 60 + m

    is_trade = False
    # 直接调用新浪交易日历API（HTTP直连，不走akshare的线程池，避免Python3.14 Errno22问题）
    try:
        import httpx
        _year = now.year
        _cal_url = f"https://tool.finance.sina.com.cn/tprice/api/tprice.php?callback=json&date={_year}"
        async with httpx.AsyncClient(timeout=10) as _c:
            _r = await _c.get(_cal_url, headers={"User-Agent": "Mozilla/5.0"})
            _text = _r.text
            # 新浪返回 jsonp 格式: json({...})
            import re
            _m = re.search(r'json\((.+)\)', _text)
            if _m:
                import json as _jmod
                _cal_data = _jmod.loads(_m.group(1))
                # 获取当年的交易日列表
                _trade_date_str = _cal_data.get("data", {}).get("date", "")
                if _trade_date_str:
                    _dates = _trade_date_str.split(",")
                    is_trade = today in _dates
    except Exception as e:
        logger.warning(f"交易日历HTTP调用失败: {e}")
    
    # 降级：HTTP方式失败时用akshare兜底（走线程池）
    if not is_trade:
        try:
            import akshare as ak
            import asyncio
            _loop = asyncio.get_event_loop()
            _df = await _loop.run_in_executor(None, lambda: ak.tool_trade_date_hist_sina())
            if _df is not None and not _df.empty:
                trade_dates = set(_df["trade_date"].astype(str))
                is_trade = today in trade_dates
        except Exception:
            pass
    
    # 最终降级：简单周末判断
    if not is_trade:
        try:
            is_trade = datetime.now().weekday() < 5
        except Exception:
            pass

    # 确定时段标签
    is_weekend = dow >= 5
    if is_weekend or not is_trade:
        session_label = "非交易日"
    elif t >= 570 and t < 690:
        session_label = "交易时段"
    elif t >= 780 and t < 897:
        session_label = "交易时段"
    elif t >= 690 and t < 780:
        session_label = "午间休市"
    elif t >= 555 and t < 560:
        session_label = "集合竞价（可撤单）"
    elif t >= 560 and t < 565:
        session_label = "集合竞价（不可撤单）"
    elif t >= 565 and t < 570:
        session_label = "开盘前等待"
    elif t >= 897 and t < 900:
        session_label = "收盘集合竞价"
    else:
        session_label = "非交易时段"

    # 计算下次开盘时间戳（毫秒）
    next_open_ts = None
    trade_dates_list = []
    try:
        import httpx
        _cal_url = f"https://tool.finance.sina.com.cn/tprice/api/tprice.php?callback=json&date={now.year}"
        async with httpx.AsyncClient(timeout=10) as _c:
            _r = await _c.get(_cal_url, headers={"User-Agent": "Mozilla/5.0"})
            import re
            _m = re.search(r'json\((.+)\)', _r.text)
            if _m:
                import json as _jmod
                _cal_data = _jmod.loads(_m.group(1))
                _date_str = _cal_data.get("data", {}).get("date", "")
                if _date_str:
                    trade_dates_list = _date_str.split(",")
    except Exception as e:
        logger.warning(f"交易日历HTTP获取失败: {e}")
    
    if trade_dates_list:
        trade_dates_list.sort()
        for td in trade_dates_list:
            if td == today:
                if t < 555:
                    next_dt = datetime.strptime(f"{td} 09:15:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=_tz)
                    next_open_ts = int(next_dt.timestamp() * 1000)
                    break
                elif t >= 900:
                    continue
                else:
                    break
            elif td > today:
                next_dt = datetime.strptime(f"{td} 09:15:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=_tz)
                next_open_ts = int(next_dt.timestamp() * 1000)
                break

    # 如果akshare计算失败，使用简单规则兜底
    if next_open_ts is None:
        try:
            if now.weekday() >= 5:  # 周末 -> 下周一 09:15
                days_ahead = 7 - now.weekday()
            elif t >= 900:  # 收盘后 -> 次日
                days_ahead = 1
                if now.weekday() == 4:  # 周五收盘 -> 下周一
                    days_ahead = 3
            else:
                days_ahead = 0
            next_date = now + timedelta(days=days_ahead if days_ahead > 0 else 0)
            # 如果当天还没开盘，当天开盘
            if t < 555 and now.weekday() < 5:
                next_dt = now.replace(hour=9, minute=15, second=0, microsecond=0)
            else:
                next_dt = next_date.replace(hour=9, minute=15, second=0, microsecond=0)
            next_open_ts = int(next_dt.timestamp() * 1000)
        except Exception:
            pass

    return {
        "is_trading_day": is_trade,
        "date": today,
        "session": session_label,
        "next_open_timestamp": next_open_ts,
    }


# ─── 巨潮资讯公告 ────────────────────────────────────────

@router.get("/announcements")
async def get_announcements(page: int = 1, page_size: int = 20):
    """获取巨潮资讯最新A股公告"""
    try:
        import httpx
        url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}
        data = {
            "pageNum": page, "pageSize": min(page_size, 50),
            "column": "szse", "tabName": "fulltext",
            "plate": "all", "stock": "", "searchkey": "", "secid": "",
            "category": "", "trade": "",
            "seDate": ["", ""],
            "sortName": "", "sortType": "", "isHLtitle": True,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, data=data, timeout=15)
            if r.status_code == 200:
                j = r.json()
                items = j.get("announcements", []) or []
                result = []
                for item in items:
                    ts = item.get("announcementTime", 0)
                    from datetime import datetime
                    dt = datetime.fromtimestamp(ts / 1000) if ts else None
                    result.append({
                        "code": item.get("secCode", ""),
                        "name": item.get("secName", ""),
                        "title": item.get("announcementTitle", ""),
                        "short_title": item.get("shortTitle", ""),
                        "date": dt.strftime("%Y-%m-%d") if dt else "",
                        "time": dt.strftime("%Y-%m-%d %H:%M") if dt else "",
                        "adjunct_url": item.get("adjunctUrl", ""),
                        "adjunct_size": item.get("adjunctSize", 0),
                        "announcement_id": item.get("announcementId", ""),
                    })
                return {"items": result, "total": j.get("totalAnnouncement", 0), "count": len(result)}
    except Exception as e:
        logger.warning(f"巨潮公告获取失败: {e}")
    return {"items": [], "total": 0, "count": 0}


# ─── 财经新闻（财联社）────────────────────────────────────

@router.get("/news")
async def get_financial_news():
    """获取最新财经新闻
    
    通过模块数据源映射 market_news 获取
    akshare_cls → 东方财富API（按 MODULE_SOURCES 优先顺序）
    确保title字段总是有值（如果为空则从content截取前20字）
    """
    dsm = _get_dsm()
    try:
        source = dsm.get_active_for_module("market_news")
        
        if source.name == "akshare_cls":
            try:
                import akshare as ak
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(None, lambda: ak.stock_info_global_cls())
                if df is not None and not df.empty:
                    title_cols = ["标题", "title", "Title", "新闻标题"]
                    content_cols = ["内容", "content", "Content", "摘要", "text", "Text"]
                    date_cols = ["发布日期", "date", "Date", "日期", "create_time"]
                    time_cols = ["发布时间", "time", "Time", "创建时间", "datetime"]
                    actual_title_col = next((c for c in title_cols if c in df.columns), None)
                    actual_content_col = next((c for c in content_cols if c in df.columns), None)
                    actual_date_col = next((c for c in date_cols if c in df.columns), None)
                    actual_time_col = next((c for c in time_cols if c in df.columns), None)
                    if actual_title_col:
                        items = []
                        for _, row in df.iterrows():
                            title = str(row.get(actual_title_col, "") or "")
                            content = str(row.get(actual_content_col, "") or "")[:300] if actual_content_col else ""
                            if not title.strip():
                                title = content[:20] if content.strip() else "未知新闻"
                            items.append({
                                "title": title, "content": content,
                                "date": str(row.get(actual_date_col, "") or "") if actual_date_col else "",
                                "time": str(row.get(actual_time_col, "") or "") if actual_time_col else "",
                            })
                        if any(i["title"].strip() for i in items):
                            return {"items": items[:50], "total": min(len(items), 50), "source": "akshare"}
            except Exception as e:
                logger.warning(f"akshare财经新闻失败: {e}")
        
        if source.name == "eastmoney":
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    news_url = "https://newsapi.eastmoney.com/QQJR/?pageNum=1&pageSize=30&type=0"
                    r = await client.get(news_url, headers={"User-Agent": "Mozilla/5.0"})
                    data = r.json()
                    items_raw = data.get("list", data.get("data", data.get("items", [])))
                    if isinstance(items_raw, dict):
                        items_raw = items_raw.get("list", [])
                    if items_raw:
                        items = []
                        for item in items_raw:
                            title = str(item.get("title", item.get("Title", item.get("art_title", ""))))
                            content = str(item.get("content", item.get("intro", item.get("Content", ""))))[:200]
                            if not title.strip() and content.strip():
                                title = content[:20]
                            if not title.strip():
                                continue
                            pub_date = str(item.get("date", item.get("Date", item.get("showDate", ""))))
                            items.append({"title": title, "content": content, "date": pub_date, "time": pub_date})
                        if items:
                            return {"items": items[:50], "total": len(items), "source": "eastmoney"}
            except Exception as e:
                logger.warning(f"东方财富新闻失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"财经新闻数据源不可用: {e}")

    # ── 降级：财联社直接爬取 ──
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                "https://www.cls.cn/telegraph",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            import re
            titles = re.findall(r'"title":"([^"]+)"', r.text)
            if titles:
                items = []
                for t in titles[:20]:
                    items.append({"title": t, "content": t, "date": "", "time": ""})
                return {"items": items, "total": len(items), "source": "cls"}
    except Exception as e3:
        logger.warning(f"财联社爬取降级失败: {e3}")

    return {"items": [], "total": 0, "source": "none"}


# ─── 单只股票行情 ─────────────────────────────────────

@router.get("/quote/{code}")
async def get_single_quote(code: str):
    """
    获取单只股票实时行情。

    参数：
    - code: 股票代码（如 000001, 600036）
    """
    dsm = _get_dsm()
    clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

    try:
        q = await dsm.get_quote(clean_code)
        if q is None:
            raise HTTPException(status_code=404, detail=f"股票 {code} 行情数据不可用")

        try:
            active_source = dsm._active_name if hasattr(dsm, '_active_name') else "unknown"
        except Exception:
            active_source = "unknown"

        return {
            "code": q.code,
            "name": q.name,
            "price": q.price,
            "open": q.open_price,
            "high": q.high_price,
            "low": q.low_price,
            "pre_close": q.pre_close,
            "change": q.change,
            "change_pct": q.change_pct,
            "volume": q.volume,
            "amount": q.amount,
            "turnover_rate": (q.turnover_rate if q.turnover_rate and q.turnover_rate > 0 else None),
            "amplitude": q.amplitude,
            "timestamp": q.timestamp.isoformat() if hasattr(q.timestamp, 'isoformat') else str(q.timestamp),
            "active_data_source": active_source,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票 {code} 行情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取行情数据失败: {str(e)}")


# ─── 分时数据 ────────────────────────────────────────────

@router.get("/timeshare/{code}")
async def get_timeshare(code: str):
    """
    获取今日分时数据（1分钟粒度）。

    参数：
    - code: 股票代码（如 000001, 600036）

    缓存策略：
    - 优先读 SQLite 本地缓存（当日数据）
    - 缓存未命中则依次尝试新浪 → 东财
    - 拉取成功后自动写入缓存
    """
    import httpx
    from backend.services.data_cache import timeshare_cache as _ts_cache

    dsm = _get_dsm()
    clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

    # 定义回调：依次尝试新浪 → 东财
    async def _fetch_from_api(raw_code: str) -> list:
        # 新浪分时
        try:
            source = dsm._sources.get("sina")
            if source and hasattr(source, 'get_timeshare'):
                result = await source.get_timeshare(raw_code)
                if result:
                    return result
        except Exception as e:
            logger.warning(f"新浪分时获取失败: {e}")

        # 东财 trend API 降级
        try:
            mkt = "1" if clean_code.startswith(("6", "9")) else "0"
            params = {
                "secid": f"{mkt}.{clean_code}",
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "ut": "fa5fd1943c7b386f172d6893dbfd32bb",
                "ndays": "1",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://push2.eastmoney.com/api/qt/stock/trends2/get",
                    params=params,
                    headers={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com"},
                )
                data = resp.json()
                trends = data.get("data", {}).get("trends", [])
                if not trends:
                    return []
                items = []
                for t in trends:
                    parts = t.split(",")
                    if len(parts) >= 6:
                        items.append({
                            "time": parts[0],
                            "price": float(parts[1]) if parts[1] else 0,
                            "avg_price": float(parts[2]) if parts[2] else 0,
                            "volume": float(parts[3]) if parts[3] else 0,
                            "amount": float(parts[4]) if parts[4] else 0,
                        })
                return items
        except Exception as e:
            logger.warning(f"东财分时降级失败: {e}")
        return []

    # 通过缓存层获取（缓存命中则跳过 API）
    items = await _ts_cache.get_or_fetch(clean_code, _fetch_from_api)

    if items:
        return {
            "code": clean_code,
            "items": items,
            "count": len(items),
            "timestamp": datetime.now().isoformat(),
            "source": "cache" if items else "api",
        }

    return {
        "code": clean_code,
        "items": [],
        "count": 0,
        "timestamp": datetime.now().isoformat(),
        "note": "分时数据暂不可用（非交易时段或数据源异常）",
    }


# ─── 技术指标 ────────────────────────────────────────────

@router.get("/indicators/{code}")
async def get_indicators(code: str):
    """
    获取技术指标（MA / MACD / KDJ / RSI）。

    参数：
    - code: 股票代码（如 000001, 600036）

    基于日线数据计算：获取120条日K线 → 计算 MA/MACD/KDJ/RSI
    """
    clean_code = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

    dsm = _get_dsm()
    try:
        klines = await dsm.get_kline(clean_code, count=120)
        if not klines:
            return {
                "code": clean_code, "ma": {}, "macd": {}, "kdj": {}, "rsi": {},
                "timestamp": datetime.now().isoformat(),
                "note": "无法获取K线数据，指标不可用",
            }

        closes = [k.close_price for k in klines]
        highs = [k.high_price for k in klines]
        lows = [k.low_price for k in klines]
        volumes = [k.volume for k in klines]

        from backend.utils.indicators import calc_ma, calc_macd, calc_kdj, calc_rsi

        # MA (取最新值)
        ma5 = calc_ma(closes, 5)
        ma10 = calc_ma(closes, 10)
        ma20 = calc_ma(closes, 20)
        ma60 = calc_ma(closes, 60)

        # MACD (取最新值)
        macd_data = calc_macd(closes)

        # KDJ (取最新值)
        kdj_data = calc_kdj(highs, lows, closes)

        # RSI (取最新值)
        rsi6 = calc_rsi(closes, 6)
        rsi12 = calc_rsi(closes, 12)
        rsi24 = calc_rsi(closes, 24)

        # 取最新值（最后一个非空）
        def _last(seq):
            for v in reversed(seq):
                if v is not None:
                    return v
            return None

        return {
            "code": clean_code,
            "ma": {
                "ma5": _last(ma5),
                "ma10": _last(ma10),
                "ma20": _last(ma20),
                "ma60": _last(ma60),
            },
            "macd": {
                "dif": _last(macd_data.get("dif", [])),
                "dea": _last(macd_data.get("dea", [])),
                "macd": _last(macd_data.get("macd_histogram", [])),
            },
            "kdj": {
                "k": _last(kdj_data.get("k", [])),
                "d": _last(kdj_data.get("d", [])),
                "j": _last(kdj_data.get("j", [])),
            },
            "rsi": {
                "rsi6": _last(rsi6),
                "rsi12": _last(rsi12),
                "rsi24": _last(rsi24),
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning(f"计算技术指标失败({clean_code}): {e}")
        return {
            "code": clean_code, "ma": {}, "macd": {}, "kdj": {}, "rsi": {},
            "timestamp": datetime.now().isoformat(), "error": str(e),
        }


# =====================================================================
# 市场扩展接口（移植自 go-stock）
# 全球指数、行业排名、资金流向等
# =====================================================================

from backend.services.market_ext import MarketExtensionService
_market_ext = MarketExtensionService()


@router.get("/global-indices")
async def global_indices():
    """全球主要指数行情（腾讯财经）"""
    return await _market_ext.get_global_indices()


@router.get("/industry-ranking")
async def industry_ranking(sort: str = "0", count: int = 20):
    return await _market_ext.get_industry_ranking(sort, count)


@router.get("/industry-money-flow")
async def industry_money_flow(sort: str = "netamount", fenlei: str = "0"):
    return await _market_ext.get_industry_money_flow(sort, fenlei)


@router.get("/stock-money-flow")
async def stock_money_flow(sort: str = "netamount"):
    return await _market_ext.get_stock_money_flow(sort)


# =====================================================================
# 新增市场扩展接口（6个）
# =====================================================================


@router.get("/stock-research-report")
async def stock_research_report(
    stock_code: str = Query(..., description="股票代码"),
    days: int = Query(365, ge=1, le=3650, description="查询天数范围"),
):
    """个股研报（东方财富 reportapi）"""
    return await _market_ext.get_stock_research_report(stock_code, days)


@router.get("/stock-notice")
async def stock_notice(
    stock_codes: str = Query(..., description="股票代码，逗号分隔"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
):
    """公司公告（东方财富）"""
    return await _market_ext.get_stock_notice(stock_codes, page_size)


@router.get("/industry-research-report")
async def industry_research_report(
    industry_code: str = Query("", description="行业代码，空字符串查全部"),
    days: int = Query(7, ge=1, le=365, description="查询天数范围"),
):
    """行业研究报告（东方财富 reportapi）"""
    return await _market_ext.get_industry_research_report(industry_code, days)


@router.post("/indicator-selection")
async def indicator_selection(
    payload: Dict[str, str],
    db: AsyncSession = Depends(get_db),
):
    """指标选股（东方财富选股器）"""
    keyword = payload.get("keyword", "")
    # 从用户偏好读取东财唯一标识
    qgqp_b_id = ""
    try:
        from sqlalchemy import select as _sl
        from backend.models.config import UserPreference
        _r = await db.execute(_sl(UserPreference).where(UserPreference.key == "eastmoney_qgqp_b_id"))
        _p = _r.scalar_one_or_none()
        if _p:
            qgqp_b_id = _p.value
    except Exception:
        pass
    return await _market_ext.get_indicator_selection(keyword, qgqp_b_id)


@router.get("/limit-up-tier")
async def limit_up_tier():
    """涨停梯队（akshare涨停股池 + 东方财富实时行情筛选兜底）"""
    dsm = _get_dsm()
    try:
        ak = dsm.get_active_for_module("market_limit")
        if hasattr(ak, "get_limit_up_pool"):
            result = await ak.get_limit_up_pool()
            if result:
                return {
                    "stocks": result,
                    "count": len(result),
                    "source": "akshare_zt_pool",
                }
    except Exception as e:
        logger.warning(f"涨停股池获取失败: {e}")
    # 降级：原来的东财实时行情筛选
    return await _market_ext.get_limit_up_tier()


@router.get("/anomaly-monitor")
async def anomaly_monitor():
    """异动监控（东方财富实时行情筛选）"""
    return await _market_ext.get_anomaly_monitor()


@router.get("/research-report-detail/{info_code}")
async def research_report_detail(info_code: str):
    """
    个股研报详情（全文）。

    从东方财富研报详情页爬取标题和正文内容。
    如果无法解析正文，返回PDF链接供前端直接打开。
    """
    return await _market_ext.get_stock_report_detail(info_code)


# ─── 第一波新接口：akshare 强化 + 情绪分析 ────────

_sentiment_service = None


def _get_sentiment_service():
    global _sentiment_service
    if _sentiment_service is None:
        from backend.services.sentiment_service import SentimentAnalysisService
        _sentiment_service = SentimentAnalysisService()
    return _sentiment_service


@router.get("/concept-sectors")
async def concept_sectors():
    """概念板块涨跌排行"""
    dsm = _get_dsm()
    # 1. akshare 东方财富概念板块
    try:
        ak = dsm.get_active_for_module("market_concept")
        if hasattr(ak, "get_concept_sectors"):
            result = await ak.get_concept_sectors()
            if result and len(result) > 0:
                return result
            logger.info("概念板块-数据源返回空，尝试降级")
    except Exception as e:
        logger.warning(f"概念板块-数据源失败: {e}")

    # 2. 降级：直调 akshare
    try:
        import akshare as _ak
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _ak.stock_board_concept_spot_em)
        if df is not None and not df.empty:
            df = df.head(20)
            result = []
            for _, r in df.iterrows():
                result.append({
                    "name": str(r.get("板块名称", "")),
                    "avg_change_pct": float(r.get("涨跌幅", 0)),
                    "leading_stock": str(r.get("龙头股", "")) if r.get("龙头股") is not None and str(r.get("龙头股")) != "nan" else "",
                    "leading_stock_change": float(r.get("龙头股涨跌幅", 0)) if r.get("龙头股涨跌幅") is not None else 0,
                })
            return result
        logger.info("概念板块-akshare返回空，尝试腾讯降级")
    except Exception as e2:
        logger.warning(f"概念板块-akshare降级失败: {e2}")

    # 3. 降级：腾讯财经概念板块 (t=02=概念, t=01=行业)
    try:
        import httpx
        _url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank?l=20&p=1&t=02/averatio&ordertype=&o=0"
        async with httpx.AsyncClient(timeout=10) as _client:
            _resp = await _client.get(_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com"})
            _data = _resp.json()
            if _data.get("code") == 0 and _data.get("data"):
                result = []
                for item in _data["data"]:
                    result.append({
                        "name": item.get("bd_name", ""),
                        "avg_change_pct": float(item.get("bd_zdf", 0)),
                        "leading_stock": item.get("nzg_name", ""),
                        "leading_stock_change": float(item.get("nzg_zdf", 0)) if item.get("nzg_zdf") else 0,
                    })
                logger.info(f"概念板块-腾讯降级(t=02): {len(result)} 条")
                return result
    except Exception as e3:
        logger.warning(f"概念板块-腾讯降级失败: {e3}")

    return []


@router.get("/industry-sectors-detailed")
async def industry_sectors_detailed():
    """行业板块详细行情（akshare）"""
    dsm = _get_dsm()
    try:
        ak = dsm.get_active_for_module("market_sector")
        if hasattr(ak, "get_industry_sectors_detailed"):
            return await ak.get_industry_sectors_detailed()
    except Exception as e:
        logger.warning(f"行业板块详细获取失败: {e}")
    return []


@router.get("/advance-decline")
async def advance_decline():
    """
    涨跌分布统计。

    缓存策略：当日数据首次拉取成功后缓存到 SQLite，后续请求直接读缓存。
    """
    from backend.services.data_cache import generic_cache
    _cache_key = "advance_decline_today"

    # 1. 读缓存
    cached = await generic_cache.get(_cache_key)
    if cached:
        import json as _json
        try:
            return _json.loads(cached)
        except Exception:
            pass

    # 2. 从 API 拉取
    import httpx
    _result = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1", "pz": "5000", "po": "0", "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2", "invt": "2", "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2",
                "fields": "f12,f3",
            }
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
            resp = await client.get(url, params=params, headers=headers)
            data = resp.json()
            items = (data.get("data", {}) or {}).get("diff", [])
            if items:
                up = 0
                down = 0
                flat = 0
                limit_up = 0
                limit_down = 0
                for it in items:
                    chg = it.get("f3")
                    if chg is None:
                        continue
                    try:
                        chg = float(chg)
                    except (ValueError, TypeError):
                        continue
                    if chg > 0:
                        up += 1
                        if chg >= 9.8:
                            limit_up += 1
                    elif chg < 0:
                        down += 1
                        if chg <= -9.8:
                            limit_down += 1
                    else:
                        flat += 1

                total = up + down + flat
                # 尝试获取第二页补齐数据
                params["pn"] = "2"
                try:
                    resp2 = await client.get(url, params=params, headers=headers)
                    data2 = resp2.json()
                    items2 = (data2.get("data", {}) or {}).get("diff", [])
                    for it in items2:
                        chg = it.get("f3")
                        if chg is None:
                            continue
                        try:
                            chg = float(chg)
                        except (ValueError, TypeError):
                            continue
                        if chg > 0:
                            up += 1
                            if chg >= 9.8:
                                limit_up += 1
                        elif chg < 0:
                            down += 1
                            if chg <= -9.8:
                                limit_down += 1
                        else:
                            flat += 1
                except Exception:
                    pass

                _result = {
                    "up": up,
                    "down": down,
                    "flat": flat,
                    "total": total,
                    "limit_up": limit_up,
                    "limit_down": limit_down,
                }
                # 写入缓存
                import json as _json
                try:
                    await generic_cache.set(_cache_key, _json.dumps(_result), ttl_seconds=3600)
                except Exception:
                    pass
                return _result
    except Exception as e:
        logger.warning(f"涨跌分布-东财失败: {e}")

    # 降级：akshare 实时行情
    try:
        import akshare as _ak
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _ak.stock_zh_a_spot_em)
        if df is not None and not df.empty and "涨跌幅" in df.columns:
            up = int((df["涨跌幅"] > 0).sum())
            down = int((df["涨跌幅"] < 0).sum())
            flat = int((df["涨跌幅"] == 0).sum())
            limit_up = int((df["涨跌幅"] >= 9.8).sum())
            limit_down = int((df["涨跌幅"] <= -9.8).sum())
            total = len(df)
            logger.info(f"涨跌分布-akshare: 上涨{up} 平盘{flat} 下跌{down} 涨停{limit_up} 跌停{limit_down}")
            _result = {
                "up": up, "down": down, "flat": flat, "total": total,
                "limit_up": limit_up, "limit_down": limit_down,
            }
            # 写入缓存
            import json as _json
            try:
                await generic_cache.set(_cache_key, _json.dumps(_result), ttl_seconds=3600)
            except Exception:
                pass
            return _result
    except Exception as e2:
        logger.warning(f"涨跌分布-akshare降级失败: {e2}")

    # 写入缓存（空结果也写，TTL短一些避免缓存太久）
    _save = _result or {"up": 0, "down": 0, "flat": 0, "total": 0, "limit_up": 0, "limit_down": 0}
    import json as _json
    try:
        _ttl = 300 if _result else 120  # 有数据1小时，无数据2分钟
        await generic_cache.set(_cache_key, _json.dumps(_save), ttl_seconds=_ttl)
        logger.info(f"涨跌分布缓存写入: {_save['up']}/{_save['flat']}/{_save['down']} TTL={_ttl}s")
    except Exception as e:
        logger.warning(f"涨跌分布缓存写入失败: {e}")

    return _save


@router.get("/individual-fund-flow/{code}")
async def individual_fund_flow(code: str):
    """个股资金流（主力/超大单/大单/中单/小单）+ 换手率

    优先通过数据源管理器获取（自带线程池隔离）。
    数据源不可用时直连 AKShare（绕过状态检查），确保数据可达。
    """
    # 方案A：通过数据源管理器
    try:
        dsm = _get_dsm()
        ak = dsm.get_active_for_module("market_fund_flow")
        if hasattr(ak, "get_individual_fund_flow"):
            result = await ak.get_individual_fund_flow(code)
            if result and isinstance(result, dict):
                tr = await _get_stock_turnover(code)
                if tr > 0:
                    result["turnover_rate"] = tr
                return result
    except Exception as e:
        logger.warning(f"个股资金流(DSM)({code}): {e}")

    # 方案B：直连 AKShare（绕过数据源 OFFLINE 状态）
    try:
        from backend.services.data_source.akshare_data import _AKSHARE_POOL
        import akshare as ak
        clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        market = "sh" if clean.startswith(("6", "9")) else "sz"
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(_AKSHARE_POOL, ak.stock_individual_fund_flow, clean, market)
        if df is not None and not df.empty:
            latest = df.iloc[-1]
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
        logger.warning(f"个股资金流(直连)({code}): {e}")
    return {}


@router.get("/anomalies")
async def batch_anomalies(codes: str = ""):
    """批量查询交易异动（利好/利空信号）"""
    if not codes:
        return {"anomalies": {}}
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not code_list:
        return {"anomalies": {}}
    try:
        dsm = _get_dsm()
        quotes = await dsm.get_quotes(code_list)
        if not quotes:
            return {"anomalies": {}}
        from backend.services.anomaly_detector import batch_detect_anomalies
        anomalies = await batch_detect_anomalies(quotes, dsm)
        return {"anomalies": anomalies}
    except Exception as e:
        logger.warning(f"批量异动查询失败: {e}")
        return {"anomalies": {}}


@router.get("/individual-info/{code}")
async def individual_info(code: str):
    """个股基本信息（行业、市盈率、总市值等）+ 换手率"""
    dsm = _get_dsm()
    try:
        ak = dsm.get_active_for_module("market_stock_info")
        if hasattr(ak, "get_individual_info"):
            result = await ak.get_individual_info(code)
            if result and isinstance(result, dict):
                tr = await _get_stock_turnover(code)
                if tr > 0:
                    result["turnover_rate"] = tr
            return result
    except Exception as e:
        logger.warning(f"个股基本信息获取失败({code}): {e}")
    return {"code": code, "error": str(e)}


@router.get("/sentiment/{code}")
async def stock_sentiment(code: str):
    """个股新闻舆情情绪分析"""
    svc = _get_sentiment_service()
    return await svc.get_sentiment(code)


@router.get("/news/{code}")
async def stock_news(code: str, days: int = Query(7, ge=1, le=30)):
    """个股相关新闻列表"""
    svc = _get_sentiment_service()
    return await svc.get_news_list(code, days)
