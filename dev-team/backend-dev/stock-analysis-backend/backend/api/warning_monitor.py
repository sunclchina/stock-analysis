"""
M03 智能预警 — 监控面板接口。

新增端点：
- GET  /warning/monitor          → 监控池所有股票的实时7模块颜色+综合
- GET  /warning/realtime/{code}   → 单只股票实时7模块颜色+综合

遵循设计文档6.智能预警模块.md 输出格式。
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cachetools import TTLCache

from backend.config.database import get_db
from backend.services.data_source.fallback import DataSourceManager

logger = logging.getLogger(__name__)

# 内存缓存：监控面板结果缓存 5 分钟
_monitor_ttl_cache: Dict[str, TTLCache] = {}

def _get_monitor_cache(user_id: int = 0) -> TTLCache:
    """获取按用户隔离的监控面板内存缓存"""
    key = str(user_id)
    if key not in _monitor_ttl_cache:
        _monitor_ttl_cache[key] = TTLCache(maxsize=1, ttl=300)  # 5分钟
    return _monitor_ttl_cache[key]

router = APIRouter(tags=["warning"], prefix="/warning")

# 全局数据源管理器引用（在_get_engine中动态获取）


def _get_engine():
    """获取预警引擎实例（从main.py延迟引用）"""
    try:
        from backend.main import warning_engine
        return warning_engine
    except (ImportError, AttributeError):
        return None


# 设计文档颜色体系映射
COLOR_EMOJI = {
    "green": "🟢",
    "yellow": "🟡",
    "red": "🔴",
    "blue": "🔵",
    "orange": "🟠",
    "black": "⚫",
    "gray": "⬜",
}

COLOR_PRIORITY = {
    "gray": 0,
    "green": 1,
    "yellow": 2,
    "orange": 3,
    "red": 4,
    "blue": 5,
    "black": 6,
}


async def _get_monitor_codes_async(user_id: int = 0) -> List[str]:
    """异步从数据库获取监控池代码列表（支持按用户过滤）"""
    try:
        from backend.models.config import MonitorItem
        from backend.config.database import async_session_factory
        from sqlalchemy import select
        async with async_session_factory() as session:
            query = select(MonitorItem).where(MonitorItem.is_active == True)
            if user_id > 0:
                query = query.where(MonitorItem.user_id == user_id)
            result = await session.execute(query)
            items = result.scalars().all()
            codes = list(dict.fromkeys(item.code for item in items))  # 去重保留顺序
            logger.info(f"从数据库加载监控池：{len(codes)} 只股票")
            return codes
    except Exception as e:
        logger.warning(f"从数据库加载监控池失败: {e}")
        return []


async def _check_single_stock(code: str, finance: dict = None, evt_data: dict = None) -> Dict[str, Any]:
    """对单只股票运行所有预警检查，返回设计文档格式的结果"""
    finance = finance or {}
    evt_data = evt_data or {"events": [], "hard_avoid": False}
    import asyncio
    from backend.services.warning_engine.price import check_warnings_for_stock
    from backend.services.warning_engine.trend import check_trend_warning
    from backend.services.warning_engine.resonance import check_resonance_warning
    from backend.services.warning_engine.finance import check_finance_warning
    from backend.services.warning_engine.event import check_event_warning
    from backend.services.warning_engine.risk import check_risk_score
    from backend.services.warning_engine.decision import compute_decision, get_highest_color

    # 默认结构
    result = {
        "code": code,
        "name": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price_warning": "gray",
        "updown_warning": "gray",
        "trend_warning": "gray",
        "resonance_warning": "gray",
        "finance_warning": "gray",
        "event_warning": "gray",
        "risk_level": "gray",
        "overall": "gray",
        "reason": "",
        "suggestion": "",
        "changes": {},
        "price_data": {},
        "trend_data": {},
        "resonance_data": {},
        "risk_data": {},
    }

    try:
        # 尝试获取股票中文名和实时行情
        name = ""
        price = 0
        pre_close = 0
        open_price = 0
        high = 0
        low = 0

        try:
            from backend.main import data_source_manager
            dsm = data_source_manager
            quote = await dsm.get_quote(code)
            if quote:
                price = quote.price or 0
                pre_close = quote.pre_close or 0
                open_price = quote.open_price or 0
                high = quote.high_price or 0
                low = quote.low_price or 0
                name = quote.name or ""
        except Exception:
            pass

        if not name:
            try:
                import httpx
                sina_code = f"sz{code}" if code.startswith(("0", "3")) else f"sh{code}"
                if code.startswith("8"):
                    sina_code = f"bj{code}"
                r = await httpx.AsyncClient(timeout=5).get(
                    f"https://hq.sinajs.cn/list={sina_code}",
                    headers={"Referer": "https://finance.sina.com.cn"}
                )
                txt = r.content.decode("gbk", errors="ignore")
                if txt and '="' in txt:
                    parts = txt.split('"')[1].split(",")
                    name = parts[0] if len(parts) > 0 else ""
            except Exception:
                pass

        result["name"] = name or code

        # 非交易时段：从TDX本地K线获取最近收盘价作为当前价格
        if price == 0 and pre_close == 0:
            try:
                from backend.main import data_source_manager as dsm2
                k_lines = await dsm2.get_kline(code, 2)
                if k_lines and len(k_lines) >= 1:
                    last = k_lines[-1]
                    if last.close_price:
                        price = last.close_price
                    if len(k_lines) >= 2:
                        pre_close = k_lines[-2].close_price
                    elif last.close_price:
                        pre_close = last.close_price * 0.98  # 近似值
                    open_price = last.open_price or price
                    high = last.high_price or price * 1.02
                    low = last.low_price or price * 0.98
                    logger.info(f"非交易时段使用K线收盘价 {code}: price={price}, pre_close={pre_close}")
            except Exception as e:
                logger.warning(f"K线价格回退失败 {code}: {e}")

        # 运行价格/涨跌预警（设计文档6.3.1规则）
        try:
            # 收集K线数据用于价格预警计算
            k_lines = []
            try:
                from backend.main import data_source_manager as dsm2
                k_lines = await dsm2.get_kline(code, 250)
            except Exception:
                pass
            closes = [k.close_price for k in (k_lines or []) if hasattr(k, 'close_price') and k.close_price]
            highs = [k.high_price for k in (k_lines or []) if hasattr(k, 'high_price') and k.high_price]
            lows = [k.low_price for k in (k_lines or []) if hasattr(k, 'low_price') and k.low_price]
            volumes = [k.volume for k in (k_lines or []) if hasattr(k, 'volume') and k.volume]

            # 用新价格预警规则计算
            from backend.services.warning_engine.price import check_price_warning_design
            pw = check_price_warning_design(code, name or "", price, closes, highs, lows, volumes)
            result["price_warning"] = pw.indicator_color
            if pw.triggered and pw.title:
                result["reason"] += pw.title + "; "

            # 涨跌预警（设计文档6.3.2规则）
            from backend.services.warning_engine.price import check_updown_warning_design
            ud = check_updown_warning_design(code, name or "", price, open_price, pre_close,
                closes=closes, volumes=volumes, is_trading_hours=False)
            result["updown_warning"] = ud.indicator_color

            # 价格数据
            change_pct = ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0
            result["price_data"] = {"price": round(price, 2), "pre_close": round(pre_close, 2), "change_pct": round(change_pct, 2), "open": round(open_price, 2)}
        except Exception as e:
            logger.warning(f"价格预警失败 {code}: {e}")

        # 运行趋势预警 — 多源获取K线数据
        has_kline_data = False
        try:
            k_lines = []
            try:
                from backend.main import data_source_manager as dsm
                logger.info(f"获取K线 {code}, dsm源数={len(dsm._sources)}")
                k_lines = await dsm.get_kline(code, 60)
                logger.info(f"K线 {code} 结果: {len(k_lines) if k_lines else 0}条")
            except Exception as e:
                logger.warning(f"获取K线 {code} 异常: {e}", exc_info=True)
            
            closes = [k.close_price for k in (k_lines or []) if hasattr(k, 'close_price') and k.close_price]
            volumes = [k.volume for k in (k_lines or []) if hasattr(k, 'volume') and k.volume]
            highs = [k.high_price for k in (k_lines or []) if hasattr(k, 'high_price') and k.high_price]
            lows = [k.low_price for k in (k_lines or []) if hasattr(k, 'low_price') and k.low_price]
            if len(closes) >= 20:
                has_kline_data = True
            # 计算均线
            from backend.utils.indicators import calc_ma
            ma5 = calc_ma(closes, 5) if len(closes) >= 5 else None
            ma10 = calc_ma(closes, 10) if len(closes) >= 10 else None
            ma20 = calc_ma(closes, 20) if len(closes) >= 20 else None
            result["trend_data"] = {
                "ma5": round(ma5[-1], 2) if ma5 and len(ma5) > 0 else None,
                "ma10": round(ma10[-1], 2) if ma10 and len(ma10) > 0 else None,
                "ma20": round(ma20[-1], 2) if ma20 and len(ma20) > 0 else None,
                "price": price or (closes[-1] if closes else None),
                "data_points": len(closes),
            }
            if closes:
                from backend.services.warning_engine.trend import check_trend_warning
                tw = check_trend_warning(code, name or "", price or closes[-1], closes,
                    volumes=volumes, highs=highs, lows=lows,
                    is_trading_hours=False)
                if tw:
                    result["trend_warning"] = tw.indicator_color
        except Exception as e:
            logger.warning(f"趋势预警失败 {code}: {e}")

        # 运行共振预警
        try:
            if has_kline_data and len(closes) >= 20:
                from backend.services.warning_engine.resonance import check_resonance_warning
                # 使用后端utils获取RSI/MACD等
                resonance_details = {}
                try:
                    from backend.utils.indicators import calc_rsi
                    rsi_vals = calc_rsi(closes, 14)
                    rsi = next((v for v in reversed(rsi_vals) if v is not None), 0)
                    resonance_details["rsi"] = {"value": round(rsi, 2)}
                except: pass
                result["resonance_data"] = resonance_details
                rw = check_resonance_warning(code, name or "", price or closes[-1], 0,
                    closes, highs or closes, lows or closes,
                    closes, volumes or [10000] * len(closes))
                if rw:
                    result["resonance_warning"] = rw.indicator_color
                    if rw.indicator_color != "gray" and rw.title:
                        if result["reason"]:
                            result["reason"] += "; "
                        result["reason"] += rw.title
        except Exception as e:
            logger.warning(f"共振预警失败 {code}: {e}")

        # 财务预警（使用预加载的财务数据）
        try:
            fw = check_finance_warning(code, name or "", price,
                pe=finance.get("pe"),
                pb=finance.get("pb"),
                revenue_growth=finance.get("revenue_growth"),
                profit_growth=finance.get("profit_growth"),
                debt_ratio=finance.get("debt_ratio"),
            )
            if fw:
                result["finance_warning"] = fw.indicator_color
        except Exception as e:
            logger.warning(f"财务预警失败 {code}: {e}")

        # 突发预警
        try:
            ew = check_event_warning(code, name or "",
                price=price, pre_close=pre_close,
                open_price=open_price, high_price=high, low_price=low,
                volumes=volumes if 'volumes' in dir() else [],
                closes=closes, event_data=evt_data)
            if ew:
                result["event_warning"] = ew.indicator_color
        except Exception as e:
            logger.warning(f"突发预警失败 {code}: {e}")

        # 风险评分（设计文档6.3.7规则）
        try:
            from backend.services.warning_engine.risk import check_risk_score
            rs = check_risk_score(
                code, name or "",
                closes=closes,
                price=price,
                pre_close=pre_close,
                volumes=volumes,
                is_trading_hours=False,
                finance_color=result.get("finance_warning", "gray"),
                event_color=result.get("event_warning", "gray"),
            )
            if rs:
                result["risk_level"] = rs.indicator_color
                import ast
                detail_dict = ast.literal_eval(rs.detail) if rs.detail and isinstance(rs.detail, str) else {}
                score_val = detail_dict.get("risk_score", 50)
                result["risk_data"] = {
                    "score": score_val,
                    "level": result["risk_level"],
                    "daily_score": detail_dict.get("daily_score", 0),
                }
                if score_val >= 61:
                    result["reason"] += f"风险{score_val:.0f}分; "
        except Exception as e:
            logger.warning(f"风险评分失败 {code}: {e}")
            result["risk_data"] = {"score": 50, "level": "gray"}

        # 综合决策 — 将各模块颜色传给compute_decision
        try:
            from backend.services.warning_engine.price import WarningResult
            warn_map = {"price_warning": "price", "updown_warning": "updown",
                "trend_warning": "trend", "resonance_warning": "resonance",
                "finance_warning": "finance", "event_warning": "event", "risk_level": "risk"}
            all_warnings = {}
            for wk, wtype in warn_map.items():
                color = result.get(wk, "gray")
                if color != "gray":
                    all_warnings[wtype] = WarningResult(
                        code=code, warning_type=wtype,
                        warning_level="info", title="", detail="",
                        indicator_color=color, triggered=True)
            decision = compute_decision(code, name or "", all_warnings)
            result["overall"] = decision.get("combined_color", "gray")
            result["suggestion"] = decision.get("suggestion_cn", "")
        except Exception:
            colors = [result[k] for k in ["price_warning", "updown_warning", "trend_warning",
                      "resonance_warning", "finance_warning", "event_warning", "risk_level"]]
            result["overall"] = max(colors, key=lambda c: {"gray": 0, "green": 1, "yellow": 2,
                "orange": 3, "red": 4, "blue": 5, "black": 6}.get(c, 0))

        result["reason"] = result["reason"].rstrip("; ")

    except Exception as e:
        logger.error(f"检查股票 {code} 预警失败: {e}")
        result["reason"] = f"检查失败: {str(e)}"

    return result


# 监控面板缓存目录
MON_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "monitor_cache")
os.makedirs(MON_CACHE_DIR, exist_ok=True)


def _load_monitor_cache(user_id: int = 0, pool_codes: list = None) -> Optional[dict]:
    """读取今日监控面板缓存（按用户隔离，检查监控池一致性）"""
    today = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_user_{user_id}" if user_id else ""
    cache_file = os.path.join(MON_CACHE_DIR, f"monitor_{today}{suffix}.json")
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            # 检查缓存中的股票是否与当前监控池一致
            if pool_codes is not None:
                cached_codes = sorted(set(item.get("code","") for item in cached.get("items",[])))
                current_codes = sorted(set(pool_codes))
                if cached_codes != current_codes:
                    logger.info(f"监控池已变更，缓存失效: {cached_codes} != {current_codes}")
                    return None
            return cached
        except Exception as e:
            logger.warning(f"监控缓存读取失败: {e}")
    return None


def _save_monitor_cache(data: dict, user_id: int = 0):
    """保存监控面板到今日缓存（按用户隔离）"""
    today = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_user_{user_id}" if user_id else ""
    cache_file = os.path.join(MON_CACHE_DIR, f"monitor_{today}{suffix}.json")
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
        logger.info(f"监控面板已缓存: {cache_file}")
    except Exception as e:
        logger.warning(f"监控缓存写入失败: {e}")


@router.get("/monitor")
async def get_monitor_panel(request: Request, force_refresh: bool = Query(False, description="强制重新计算")):
    """
    监控面板：返回监控池所有股票预警状态。

    非交易时段每天计算一次并缓存，其余时间返回缓存。
    force_refresh=True 时强制重新计算并更新缓存。
    如果监控池发生变更，缓存自动失效。

    输出格式遵循设计文档6.4节，每只股票返回：
    - code/name/timestamp
    - price_warning / updown_warning / trend_warning
    - resonance_warning / finance_warning / event_warning
    - risk_level / overall / reason / changes
    """
    # 从请求头解析当前用户
    user_id = 0
    if request:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            from backend.services.auth_service import decode_token
            payload = decode_token(auth[7:])
            if payload:
                try:
                    user_id = int(payload.get("sub", 0))
                except (ValueError, TypeError):
                    user_id = 0

    codes = await _get_monitor_codes_async(user_id=user_id)
    # 去重（防止同一股票因多次添加而重复）
    seen = set()
    unique_codes = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            unique_codes.append(c)
    codes = unique_codes
    if not codes:
        return {"items": [], "total": 0, "timestamp": datetime.now().isoformat()}

    # 非强制刷新时尝试内存缓存（TTLCache 5分钟）
    if not force_refresh:
        mem_cache = _get_monitor_cache(user_id)
        cached_key = f"monitor_panel_{user_id}"
        if cached_key in mem_cache:
            cached_data = mem_cache[cached_key]
            # 验证监控池一致性
            cached_codes = sorted(set(item.get("code","") for item in cached_data.get("items",[])))
            current_codes = sorted(set(codes))
            if cached_codes == current_codes:
                cached_data["from_cache"] = True
                return cached_data

    # 非强制刷新时尝试文件缓存（需拿到监控池列表后验证一致性）
    if not force_refresh:
        cached = _load_monitor_cache(user_id=user_id, pool_codes=codes)
        if cached:
            cached["from_cache"] = True
            return cached

    import asyncio
    from backend.services.warning_engine.price import check_warnings_for_stock
    from backend.services.warning_engine.trend import check_trend_warning
    from backend.services.warning_engine.resonance import check_resonance_warning
    from backend.services.finance_enricher import fetch_finance_bulk
    from backend.services.warning_engine.finance import check_finance_warning
    from backend.services.warning_engine.event import check_event_warning, EVENT_WEIGHTS, ALL_EVENTS, HARD_AVOID_EVENTS
    from backend.services.warning_engine.risk import check_risk_score
    from backend.services.warning_engine.decision import compute_decision, get_highest_color

    # 批量预加载财务数据
    loop = asyncio.get_event_loop()
    all_finance = await loop.run_in_executor(None, fetch_finance_bulk, codes)
    
    # 批量预加载事件数据（一次性查CNINFO，所有股票共享）
    all_events = {}
    try:
        from backend.services.event_detector import fetch_all_events
        event_result = await loop.run_in_executor(None, fetch_all_events)
        for item in event_result.get("items", []):
            code = item["code"]
            events = []
            hard_avoid = False
            for e in item["events"]:
                evt_key = None
                if "财务造假" in e["label"]:
                    evt_key = "fraud_investigation"
                    hard_avoid = True
                elif "否定" in e["label"] or "无法表示" in e["label"]:
                    evt_key = "audit_negative_opinion"
                    hard_avoid = True
                elif "债务违约" in e["label"]:
                    evt_key = "debt_default"
                    hard_avoid = True
                elif "谴责" in e["label"] or "处罚" in e["label"]:
                    evt_key = "public_censure"
                elif "差错更正" in e["label"]:
                    evt_key = "accounting_error"
                if evt_key and evt_key in EVENT_WEIGHTS:
                    events.append({"key": evt_key, "name": ALL_EVENTS.get(evt_key, e["label"]), "weight": EVENT_WEIGHTS[evt_key]})
            all_events[code] = {"events": events, "hard_avoid": hard_avoid}
        logger.info(f"预警引擎: 事件数据就绪 ({len(all_events)} 只)")
    except Exception as e:
        logger.warning(f"预警引擎: 事件数据加载失败 {e}")

    tasks = [_check_single_stock(code, all_finance.get(code, {}), all_events.get(code, {"events": [], "hard_avoid": False})) for code in codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    errors = 0
    for r in results:
        if isinstance(r, Exception):
            errors += 1
        else:
            items.append(r)

    result = {
        "items": items,
        "total": len(items),
        "errors": errors,
        "timestamp": datetime.now().isoformat(),
        "from_cache": False,
    }

    # 保存到内存缓存
    try:
        mem_cache = _get_monitor_cache(user_id)
        mem_cache[f"monitor_panel_{user_id}"] = result
    except Exception:
        pass

    # 保存到今日缓存（文件）
    _save_monitor_cache(result, user_id=user_id)

    return result


@router.get("/realtime/{code}")
async def get_stock_realtime(code: str):
    """
    单只股票实时预警监控。

    返回该股票7模块颜色+综合+详细原因。
    """
    result = await _check_single_stock(code)
    if not result.get("name"):
        result["name"] = code
    return result
