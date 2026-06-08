"""
M05 智能分析模块API。

遵循架构方案4.1节 M05接口定义：
- POST /review        → 盘后复盘分析
- POST /stock         → 个股分析
- POST /batch         → 批量分析（≤10只）
- GET  /download/{id} → 下载分析报告（Markdown/TXT）
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Body, Query, Path, Request
from fastapi.responses import PlainTextResponse

from backend.services.analysis_engine import (
    generate_review,
    analyze_stock,
    batch_analyze,
    LLMClient,
)

logger = logging.getLogger(__name__)


def _get_user_id(request=None) -> int:
    """从请求头解析当前用户ID"""
    if request is None:
        return 0
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return 0
    from backend.services.auth_service import decode_token
    payload = decode_token(auth[7:])
    if not payload:
        return 0
    try:
        return int(payload.get("sub", 0))
    except (ValueError, TypeError):
        return 0


router = APIRouter(tags=["analysis"], prefix="/analysis")

# 报告存储目录
REPORTS_DIR = "./data/reports"


# ─── 数据提供回调 ─────────────────────────────────

async def _get_market_overview() -> Dict[str, Any]:
    """获取大盘概览数据"""
    try:
        from backend.api.market import market_overview
        result = await market_overview()
        return result
    except Exception as e:
        logger.warning(f"获取大盘概览失败: {e}")
        return {"error": str(e), "items": []}


async def _get_stock_quotes(codes: List[str]) -> Dict[str, Any]:
    """批量获取个股行情"""
    try:
        from backend.api.market import batch_quotes
        codes_str = ",".join(codes)
        result = await batch_quotes(codes_str)
        return result
    except Exception as e:
        logger.warning(f"获取个股行情失败: {e}")
        return {"error": str(e)}


async def _get_stock_quote_single(code: str) -> Dict[str, Any]:
    """获取单只股票行情"""
    try:
        from backend.api.market import get_single_quote
        return await get_single_quote(code)
    except Exception as e:
        logger.warning(f"获取个股行情 [{code}] 失败: {e}")
        return {"error": str(e), "code": code}


async def _get_kline_data(code: str) -> List[Dict[str, Any]]:
    """获取K线数据（带持久缓存，周末/节假日回读缓存）"""
    # 先从API获取
    klines = []
    try:
        from backend.api.market import get_kline
        result = await get_kline(code, count=120, period="daily")
        klines = result.get("klines", [])
    except Exception as e:
        logger.debug(f"获取K线 [{code}] 失败: {e}")
    
    # API成功：写入缓存
    if klines:
        try:
            from backend.services.kline_cache import kline_cache_save
            kline_cache_save(code, klines)
        except Exception:
            pass
        return klines
    
    # API失败（周末/节假日）：读缓存
    try:
        from backend.services.kline_cache import kline_cache_load
        cached = kline_cache_load(code)
        if cached:
            logger.debug(f"K线读缓存: {code} ({len(cached)}条)")
            return cached
    except Exception:
        pass
    
    return []


async def _get_finance_data(code: str) -> Dict[str, Any]:
    """获取财务数据"""
    try:
        from backend.main import data_source_manager as dsm
        from backend.main import warning_engine
        cache = warning_engine._finance_cache if hasattr(warning_engine, '_finance_cache') else {}
        fin = cache.get(code, {})
        if fin:
            return {
                "code": code,
                "pe": fin.get("pe"),
                "pb": fin.get("pb"),
                "roe": fin.get("roe"),
                "revenue_growth": fin.get("revenue_growth"),
                "profit_growth": fin.get("profit_growth"),
                "debt_ratio": fin.get("debt_ratio"),
                "turnover_rate": fin.get("turnover_rate"),
                "source": "cache",
            }
    except Exception as e:
        logger.warning(f"获取财务数据 [{code}] 失败: {e}")

    # 财务缓存不可用时，返回占位结构让AI用联网搜索补充
    return {
        "code": code,
        "source": "web_search_estimated",
        "note": "实时财务API暂不可用，请通过联网搜索获取该股票的PE、PB、ROE、营收增速、利润增速、资产负债率等核心财务指标，并基于搜索到的数据进行分析。"
    }


async def _get_warning_data(code_or_codes: str) -> Dict[str, Any]:
    """获取股票预警数据"""
    try:
        from backend.main import warning_engine
        engine = warning_engine
        from backend.services.warning_engine.price import WarningResult

        # 获取预警结果（从预警引擎的缓存中获取）
        if hasattr(engine, '_previous_colors'):
            prev_colors = engine._previous_colors
            warning_info = {}
            for key, color in prev_colors.items():
                stock_code, wtype = key.split(":", 1) if ":" in key else (key, "unknown")
                if stock_code == code_or_codes or code_or_codes in stock_code:
                    if stock_code not in warning_info:
                        warning_info[stock_code] = {}
                    warning_info[stock_code][wtype] = color
            return warning_info

        return {"note": "预警引擎未运行或无数据"}
    except Exception as e:
        logger.warning(f"获取预警数据失败: {e}")
        return {"error": str(e)}


async def _get_decision_data(code: str) -> Dict[str, Any]:
    """获取综合决策矩阵数据"""
    try:
        from backend.services.warning_engine.decision import compute_decision
        # 用默认数据构造
        return {
            "code": code,
            "note": "综合决策矩阵数据需要预警引擎运行后获取",
        }
    except Exception as e:
        logger.warning(f"获取决策数据 [{code}] 失败: {e}")
        return {"error": str(e)}


async def _get_batch_stock_data(codes: List[str]) -> Dict[str, Any]:
    """批量获取股票完整数据"""
    try:
        quotes_result = await _get_stock_quotes(codes)
        stocks = {}
        for q in quotes_result.get("quotes", []):
            code = q.get("code", "")
            stocks[code] = q
        return {
            "stocks": stocks,
            "count": len(stocks),
        }
    except Exception as e:
        logger.warning(f"批量获取股票数据失败: {e}")
        return {"error": str(e)}


async def _get_warning_summary(codes: List[str]) -> Dict[str, Any]:
    """获取预警汇总数据"""
    try:
        from backend.main import warning_engine
        engine = warning_engine
        if hasattr(engine, '_previous_colors'):
            prev_colors = engine._previous_colors
            summary = {}
            for key, color in prev_colors.items():
                parts = key.split(":", 1)
                if len(parts) == 2:
                    stock_code, wtype = parts
                    if stock_code in codes:
                        if stock_code not in summary:
                            summary[stock_code] = {}
                        summary[stock_code][wtype] = color
            return summary
        return {}
    except Exception as e:
        logger.warning(f"获取预警汇总失败: {e}")
        return {}


def _save_report(report_data: Dict[str, Any], user_id: int = 0) -> Optional[str]:
    """
    保存分析报告到文件。

    Returns:
        报告ID（文件路径标识）
    """
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_type = report_data.get("report_type", "unknown")
        code = report_data.get("code", report_data.get("date", "batch"))

        filename = f"{report_type}_{code}_{timestamp}.md"
        filepath = os.path.join(REPORTS_DIR, filename)

        content = report_data.get("report", "# 报告内容为空")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # 同时保存元数据
        meta = {k: v for k, v in report_data.items() if k != "report"}
        meta["report_title"] = report_data.get("report_title", f"{report_type}分析_{code}")
        if user_id:
            meta["user_id"] = user_id
        meta_path = os.path.join(REPORTS_DIR, f"{filename}.meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, default=str)

        logger.info(f"报告已保存: {filepath}")
        return filename
    except Exception as e:
        logger.error(f"保存报告失败: {e}")
        return None


# ─── API端点 ─────────────────────────────────────────

@router.post("/review")
async def api_post_review(
    body: Dict[str, Any] = Body(...,
        examples={"default": {"value": {
            "date": "2026-04-29",
            "watch_stocks": ["000001", "600519", "000858"],
        }}},
    ),
    request: Request = None,
):
    """
    盘后复盘分析。

    输入日期+关注股票列表，生成结构化复盘报告。
    """
    date = body.get("date", datetime.now().strftime("%Y-%m-%d"))
    watch_stocks = body.get("watch_stocks", [])
    use_template = body.get("use_template", True)

    if len(watch_stocks) > 10:
        watch_stocks = watch_stocks[:10]
        logger.warning(f"复盘分析最多10只关注股票，已截断")

    result = await generate_review(
        date_str=date,
        watch_stocks=watch_stocks,
        market_data_provider=_get_market_overview,
        stock_data_provider=_get_stock_quotes,
        warning_data_provider=_get_warning_summary,
        use_template=use_template,
    )

    # 保存报告
    result["report_title"] = f"复盘分析_{date}"
    result["report_type"] = "review"
    result["date"] = date
    uid = _get_user_id(request)
    report_id = _save_report(result, uid)

    response = {
        "status": result.get("status", "failed"),
        "date": date,
        "report": result.get("report", ""),
        "report_type": "review",
        "watch_stocks": watch_stocks,
        "report_id": report_id,
        "use_template": use_template,
        "generated_at": datetime.now().isoformat(),
    }

    if result.get("error"):
        response["error"] = result["error"]

    return response


@router.post("/stock")
async def api_stock_analysis(
    body: Dict[str, Any] = Body(...,
        examples={"default": {"value": {
            "code": "000001",
        }}},
    ),
    request: Request = None,
):
    """
    个股分析。

    输入股票代码，输出完整分析报告（技术面+基本面+预警+综合结论）。
    """
    code = body.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    use_template = body.get("use_template", True)

    result = await analyze_stock(
        code=code,
        market_data_provider=lambda c: _get_stock_quote_single(c),
        kline_data_provider=_get_kline_data,
        finance_data_provider=_get_finance_data,
        warning_data_provider=_get_warning_data,
        decision_data_provider=_get_decision_data,
        use_template=use_template,
    )

    # 保存报告
    result["report_title"] = f"个股分析_{code}"
    result["report_type"] = "stock"
    result["code"] = code
    uid = _get_user_id(request)
    report_id = _save_report(result, uid)

    response = {
        "status": result.get("status", "failed"),
        "code": code,
        "name": result.get("name", ""),
        "report": result.get("report", ""),
        "report_type": "stock",
        "report_id": report_id,
        "use_template": use_template,
        "generated_at": datetime.now().isoformat(),
    }

    if result.get("error"):
        response["error"] = result["error"]

    return response


@router.post("/batch")
async def api_batch_analysis(
    body: Dict[str, Any] = Body(...,
        examples={"default": {"value": {
            "codes": ["600519", "000858", "600036"],
        }}},
    ),
):
    """
    批量分析。

    输入股票列表（≤10只），逐只分析+汇总对比。
    """
    codes = body.get("codes", [])

    if not codes:
        raise HTTPException(status_code=400, detail="股票代码列表不能为空")

    if len(codes) > 10:
        codes = codes[:10]
        logger.warning(f"批量分析最多10只，已截断")

    use_template = body.get("use_template", True)

    result = await batch_analyze(
        codes=codes,
        stock_data_provider=_get_batch_stock_data,
        warning_data_provider=_get_warning_summary,
        use_template=use_template,
    )

    # 保存报告
    result["report_title"] = f"批量分析_{len(codes)}只_{datetime.now().strftime('%m%d')}"
    result["report_type"] = "batch"
    result["codes"] = codes
    uid = _get_user_id(request)
    report_id = _save_report(result, uid)

    response = {
        "status": result.get("status", "failed"),
        "codes": codes,
        "report": result.get("report", ""),
        "report_type": "batch",
        "items_analyzed": result.get("items_analyzed", 0),
        "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
    }

    if result.get("error"):
        response["error"] = result["error"]

    return response


# ─── 形态选股 ────────────────────────────────────────────

PATTERN_ANALYSIS_PROMPT = """你是资深A股技术分析师，擅长K线形态识别。

请分析以下股票的K线数据，识别是否存在经典技术形态，并给出判断。

## 分析要求
请逐一回答以下问题，对每个问题给出"是/否/部分符合"的判断和详细理由：

### 1. 均线形态
- 5日、10日、20日、30日、60日均线是否多头排列（短>长）？
- 均线是否出现金叉/死叉信号？
- 股价是否站上关键均线（20日/60日）？

### 2. K线组合形态
- 是否出现头肩顶/底形态？
- 是否出现双顶/双底（W底/M顶）形态？
- 是否出现圆弧底/顶形态？
- 是否出现V形反转形态？
- 是否出现上升/下降旗形？
- 是否出现收敛三角形/扩散三角形？

### 3. 量价关系
- 近期是否价涨量增、价跌量缩（健康上涨）？
- 是否出现放量突破关键位置？
- 是否出现缩量回调（回踩确认）？

### 4. 技术指标
- MACD是否金叉/死叉/顶背离/底背离？
- KDJ是否超买/超卖/金叉/死叉？
- RSI是否处于强势区（>50）或超买（>80）/超卖（<20）？
- BOLL是否突破中轨/上轨/下轨？

### 5. 综合判断
- 当前趋势是上涨/下跌/震荡？
- 短线（1-5日）看涨/看跌/震荡概率？
- 中线（1-4周）看涨/看跌/震荡概率？
- 关键支撑位和压力位分别在什么价位？
- 给出总体评分：强烈看涨/看涨/中性/看跌/强烈看跌

## K线数据（最近{day_count}个交易日）
```
日期 | 开盘 | 收盘 | 最高 | 最低 | 成交量 | 成交额
{klines}
```

请用简洁的中文回答，以结构化Markdown呈现，每个形态是否出现给出明确标记（✅/❌/⚠️）。
"""


@router.post("/pattern")
async def api_pattern_scan(
    body: Dict[str, Any],
):
    """
    形态选股：从股票池中扫描符合K线形态的股票。

    输入：
    - source: 股票池来源（"all"全市场, "watchlist"自选股, "monitor"监控池）
    - pattern: 要识别的形态（ma_bullish/golden_cross/death_cross/volume_breakout/pullback/macd_golden）
    - max: 最大返回数量

    返回匹配的股票列表，按匹配强度排序。
    纯算法计算，不依赖AI，适合批量扫描。
    """
    source = body.get("source", "monitor")
    pattern_key = body.get("pattern", "ma_bullish")
    max_stocks = min(body.get("max", 50), 100)

    # 获取股票代码列表
    codes = []
    try:
        if source == "watchlist":
            from sqlalchemy import select as _sl
            from backend.config.database import async_session_factory
            from backend.models.config import WatchlistItem
            async with async_session_factory() as _db:
                _r = await _db.execute(_sl(WatchlistItem).where(WatchlistItem.is_active == True))
                codes = [i.code for i in _r.scalars().all()]
        elif source == "monitor":
            from sqlalchemy import select as _sl
            from backend.config.database import async_session_factory
            from backend.models.config import MonitorItem
            async with async_session_factory() as _db:
                _r = await _db.execute(_sl(MonitorItem).where(MonitorItem.is_active == True))
                codes = [i.code for i in _r.scalars().all()]
        elif source == "all":
            # 全市场股票列表（akshare 保证包含所有A股）
            try:
                import akshare as _ak
                import pandas as _pd
                _df = _ak.stock_info_a_code_name()
                if _df is not None and not _df.empty:
                    codes = _df['code'].astype(str).tolist()
                    if codes:
                        logger.info(f"全市场股票代码(akshare): {len(codes)} 只")
            except Exception as e:
                logger.warning(f"AkShare全市场代码获取失败: {e}")
    except Exception as e:
        logger.warning(f"股票池获取异常: {e}")

    if not codes:
        # 默认：自选股+监控池
        try:
            from sqlalchemy import select as _sl
            from backend.config.database import async_session_factory
            from backend.models.config import WatchlistItem, MonitorItem
            async with async_session_factory() as _db:
                _r1 = await _db.execute(_sl(WatchlistItem).where(WatchlistItem.is_active == True))
                _r2 = await _db.execute(_sl(MonitorItem).where(MonitorItem.is_active == True))
                codes = list(set(
                    [i.code for i in _r1.scalars().all()] +
                    [i.code for i in _r2.scalars().all()]
                ))
        except Exception:
            pass

    if not codes:
        return {"status": "failed", "error": "股票池为空，请先添加自选股或监控股", "stocks": [], "count": 0}

    # 执行扫描
    try:
        from backend.services.pattern_scanner import scan_pattern, PATTERN_REGISTRY

        pattern_info = PATTERN_REGISTRY.get(pattern_key, {})
        results = await scan_pattern(
            codes=codes,
            pattern_key=pattern_key,
            kline_provider=_get_kline_data,
            max_stocks=max_stocks,
        )

        # 补充股票名称（从行情接口获取更可靠）
        if results:
            try:
                from backend.api.market import _get_dsm
                _dsm = _get_dsm()
                _codes = [s['code'] for s in results if s.get('code')]
                _quotes = await _dsm.get_quotes(_codes)
                if _quotes:
                    _name_map2 = {q.code: q.name for q in _quotes}
                    for s in results:
                        s['name'] = _name_map2.get(s['code'], s.get('name', ''))
            except Exception as e:
                logger.warning(f"名称行情获取失败: {e}")

        return {
            "status": "ok",
            "stocks": results,
            "count": len(results),
            "pattern": pattern_key,
            "pattern_name": pattern_info.get("name", pattern_key),
            "source": source,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"形态扫描失败: {e}")
        return {"status": "failed", "error": str(e), "stocks": [], "count": 0}


@router.get("/download/{report_id}")
async def download_report(
    report_id: str = Path(..., description="报告文件名"),
    format: str = Query("markdown", pattern="^(markdown|txt)$", description="下载格式"),
):
    """
    下载分析报告。

    参数：
    - report_id: 报告文件名（如 review_20260429_183000.md）
    - format: 下载格式（markdown/txt）

    返回原始Markdown/TXT文件内容。
    """
    # 安全检查：防止目录遍历
    import os.path
    safe_filename = os.path.basename(report_id)
    filepath = os.path.join(REPORTS_DIR, safe_filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"报告 {report_id} 不存在")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        media_type = "text/markdown" if format == "markdown" else "text/plain"
        return PlainTextResponse(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"',
            },
        )
    except Exception as e:
        logger.error(f"读取报告失败 [{report_id}]: {e}")
        raise HTTPException(status_code=500, detail=f"读取报告失败: {str(e)}")


@router.get("/reports")
async def list_reports(request: Request = None):
    """
    列出当前用户的分析报告。
    """
    uid = _get_user_id(request)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    items = []
    for fname in os.listdir(REPORTS_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(REPORTS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        meta_path = fpath + ".meta.json"
        if not os.path.isfile(meta_path):
            continue
        meta = {}
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        rpt_uid = meta.get("user_id", 0)
        if rpt_uid != 0 and rpt_uid != uid:
            continue
        mtime = os.path.getmtime(fpath)
        size = os.path.getsize(fpath)
        # 读取前100字作为预览
        preview = ""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                preview = f.read(200).strip()[:80]
        except Exception:
            pass
        items.append({
            "id": fname,
            "title": meta.get("report_title", fname),
            "type": meta.get("report_type", fname.split("_")[0] if "_" in fname else "unknown"),
            "date": meta.get("date", ""),
            "created_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
            "size": size,
            "preview": preview,
        })
    # 按时间倒序
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"items": items, "total": len(items)}


@router.delete("/report/{report_id}")
async def delete_report(
    report_id: str = Path(..., description="报告文件名"),
    request: Request = None,
):
    """删除指定分析报告（仅限本人）"""
    uid = _get_user_id(request)
    import os.path
    safe = os.path.basename(report_id)
    fpath = os.path.join(REPORTS_DIR, safe)
    meta_path = fpath + ".meta.json"
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            rpt_uid = meta.get("user_id", 0)
            if rpt_uid != 0 and rpt_uid != uid:
                return {"status": "error", "message": "无权删除他人报告"}
        except Exception:
            pass
    if os.path.isfile(fpath):
        os.remove(fpath)
    if os.path.isfile(meta_path):
        os.remove(meta_path)
    return {"status": "ok", "deleted": safe}
