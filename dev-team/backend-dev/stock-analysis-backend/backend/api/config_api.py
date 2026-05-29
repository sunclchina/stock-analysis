"""
M06 系统配置模块API — 完整实现。

遵循架构方案4.1节 M06 配置接口定义 + 5.5节配置管理数据流：
- GET    /api/v1/config                  → 获取全部配置
- PUT    /api/v1/config                  → 保存全部配置
- GET    /api/v1/config/watchlist        → 自选股列表
- POST   /api/v1/config/watchlist        → 添加自选股
- DELETE /api/v1/config/watchlist/{code} → 删除自选股
- GET    /api/v1/config/monitor          → 监控池列表
- POST   /api/v1/config/monitor          → 添加监控标的
- DELETE /api/v1/config/monitor/{code}   → 删除监控标的
- GET    /api/v1/config/datasource       → 数据源状态
- POST   /api/v1/config/datasource/switch → 切换数据源
- GET    /api/v1/config/templates        → 模板列表
- POST   /api/v1/config/templates        → 保存模板
- DELETE /api/v1/config/templates/{name} → 删除模板
- GET    /api/v1/config/preferences      → 用户偏好
- PUT    /api/v1/config/preferences      → 更新偏好
- GET    /api/v1/config/system           → 系统状态

配置变更时通过 WebSocket 推送 config:changed 事件。
所有数据持久化到 SQLite。

遵循原则②：所有配置项从 settings 读取，不硬编码。
"""

import json
import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, delete, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.config.settings import settings
from backend.models.config import WatchlistItem, MonitorItem, UserPreference
from backend.services.websocket_manager import ws_manager
from backend.services.auth_service import decode_token

# 避免循环导入，延迟获取 data_source_manager
_data_source_manager = None

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])


def _get_user_id(request=None) -> int:
    """从请求头解析当前用户ID，默认1"""
    if request is None:
        return 1
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return 1
    payload = decode_token(auth[7:])
    if not payload:
        return 1
    try:
        return int(payload.get("sub", 1))
    except (ValueError, TypeError):
        return 1


def _get_dsm():
    """延迟获取数据源管理器"""
    global _data_source_manager
    if _data_source_manager is None:
        from backend.main import data_source_manager
        _data_source_manager = data_source_manager
    return _data_source_manager


async def _push_config_change(change_type: str):
    """配置变更时通过 WebSocket 推送"""
    try:
        await ws_manager.broadcast_config_change(change_type)
    except Exception as e:
        logger.warning(f"WebSocket推送配置变更失败: {e}")


async def _sina_query_name(code: str, prefix: str) -> str:
    """向新浪查询单只股票名称，prefix 为 sh/sz"""
    import httpx
    url = f"https://hq.sinajs.cn/list={prefix}{code}"
    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, headers={"Referer": "https://finance.sina.com.cn"})
        raw = resp.content.decode("gbk", errors="ignore")
        start = raw.find('"')
        end = raw.rfind('"')
        if start != -1 and end != -1:
            parts = raw[start + 1:end].split(",")
            if len(parts) >= 2 and parts[0]:
                name = parts[0].strip()
                if not name.isdigit() and len(name) >= 2:
                    return name
    return ""


async def resolve_stock_name(code: str) -> str:
    """
    通过数据源查询股票的真实中文名称。
    按优先级：数据源管理器 → 新浪（分别试 SH/SZ）
    """
    # 1) 优先通过数据源管理器查询
    try:
        from backend.main import data_source_manager
        dsm = data_source_manager
        quote = await dsm.get_quote(code)
        if quote and quote.name and not quote.name.isdigit() and len(quote.name) >= 2:
            return quote.name.strip()
    except Exception:
        pass

    # 2) 新浪接口（6开头上交所，其他先试深市再试沪市）
    clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    if clean.startswith(("6", "9")):
        prefixes = ["sh"]
    else:
        prefixes = ["sz", "sh"]  # 深市优先，沪市兜底（避免000001被误当上证指数）
    for prefix in prefixes:
        try:
            name = await _sina_query_name(clean, prefix)
            if name:
                return name
        except Exception:
            continue

    return code  # 兜底


# ─── 配置通用接口 ──────────────────────────────────────

@router.get("/config")
async def get_all_config(db: AsyncSession = Depends(get_db)):
    """
    获取全部系统配置。
    返回：环境变量配置 + 自选股列表 + 监控池 + 用户偏好 + 数据源状态。
    """
    # 环境变量配置（不暴露敏感信息）
    env_config = {
        "backend_host": settings.backend_host,
        "backend_port": settings.backend_port,
        "database_url": "***sqlite***" if "sqlite" in settings.database_url else settings.database_url,
        "primary_data_source": settings.primary_data_source,
        "fallback_data_source": settings.fallback_data_source,
        "log_level": settings.log_level,
        "tdx_data_dir": settings.tdx_data_dir,
    }

    # 自选股列表
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.is_active == True)
        .order_by(WatchlistItem.sort_order)
    )
    watchlist = [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "added_reason": item.added_reason,
            "sort_order": item.sort_order,
            "is_active": item.is_active,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in result.scalars().all()
    ]

    # 监控池
    result = await db.execute(
        select(MonitorItem)
        .where(MonitorItem.is_active == True)
        .order_by(MonitorItem.id)
    )
    monitor_pool = [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "monitor_type": item.monitor_type,
            "threshold_high": item.threshold_high,
            "threshold_low": item.threshold_low,
            "is_active": item.is_active,
        }
        for item in result.scalars().all()
    ]

    # 用户偏好
    pref_result = await db.execute(select(UserPreference))
    preferences = {
        pref.key: pref.value
        for pref in pref_result.scalars().all()
    }

    # 数据源状态
    try:
        dsm = _get_dsm()
        data_sources = dsm.get_status_summary()
    except Exception:
        data_sources = []

    return {
        "config": env_config,
        "watchlist": watchlist,
        "monitor_pool": monitor_pool,
        "preferences": preferences,
        "data_sources": data_sources,
    }


@router.put("/config")
async def save_all_config(
    config_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    保存全部配置。
    持久化配置写入数据库，环境变量配置仅提示重启生效。
    """
    changed = False

    # 处理偏好更新
    preferences = config_data.get("preferences", {})
    if preferences:
        for key, value in preferences.items():
            stmt = select(UserPreference).where(UserPreference.key == key)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = str(value)
            else:
                db.add(UserPreference(key=key, value=str(value)))
        changed = True

    if changed:
        await db.commit()
        await _push_config_change("config:updated")

    return {"status": "ok", "message": "配置已保存"}


# ─── 自选股接口 ──────────────────────────────────────

@router.get("/config/watchlist")
async def get_watchlist(db: AsyncSession = Depends(get_db), request: Request = None):
    """获取自选股列表（按用户隔离）。"""
    uid = _get_user_id(request)
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.is_active == True, WatchlistItem.user_id == uid)
        .order_by(WatchlistItem.sort_order)
    )
    items = result.scalars().all()
    output = []
    for item in items:
        # 懒加载：自动补全缺失的股票名称
        name = item.name
        if not name or name == item.code or len(name) <= 2:
            resolved = await resolve_stock_name(item.code)
            if resolved and resolved != item.code:
                name = resolved
                item.name = name
                try:
                    await db.commit()
                except Exception:
                    pass
        output.append({
            "id": item.id,
            "code": item.code,
            "name": name,
            "added_reason": item.added_reason,
            "sort_order": item.sort_order,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    return output


@router.post("/config/watchlist")
async def add_watchlist(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """添加自选股（按用户隔离）。"""
    uid = _get_user_id(request)
    code = data.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    # 检查是否已存在（仅当前用户）
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.code == code, WatchlistItem.user_id == uid)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail=f"股票 {code} 已在自选股中")
        # 重新启用
        existing.is_active = True
        name = data.get("name", "").strip()
        if not name or name == code or len(name) <= 2:
            resolved = await resolve_stock_name(code)
            if resolved and resolved != code:
                name = resolved
        existing.name = name
        existing.added_reason = data.get("added_reason", existing.added_reason)
        existing.sort_order = data.get("sort_order", existing.sort_order)
        await db.commit()
        await _push_config_change("watchlist:added")
        return {"status": "ok", "message": f"股票 {code} 已重新加入自选股", "id": existing.id}

    # 获取股票名称：优先用前端传入的，否则自动查询
    name = data.get("name", "").strip()
    if not name or name == code or len(name) <= 2:
        resolved = await resolve_stock_name(code)
        if resolved and resolved != code:
            name = resolved

    item = WatchlistItem(
        code=code, user_id=uid,
        name=name,
        added_reason=data.get("added_reason", ""),
        sort_order=data.get("sort_order", 0),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await _push_config_change("watchlist:added")

    return {"status": "ok", "message": f"股票 {code} 已添加至自选股", "id": item.id}


@router.put("/config/watchlist/{code}")
async def update_watchlist(
    code: str,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """更新自选股信息（名称、排序、原因等）。"""
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.code == code)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不在自选股中")

    if "name" in data:
        item.name = data["name"]
    if "added_reason" in data:
        item.added_reason = data["added_reason"]
    if "sort_order" in data:
        item.sort_order = data["sort_order"]
    if "is_active" in data:
        item.is_active = data["is_active"]

    await db.commit()
    await _push_config_change("watchlist:updated")
    return {"status": "ok", "message": f"股票 {code} 已更新"}


@router.delete("/config/watchlist/{code}")
async def delete_watchlist(code: str, db: AsyncSession = Depends(get_db)):
    """删除自选股（软删除）。"""
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.code == code)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不在自选股中")

    # 软删除
    item.is_active = False
    await db.commit()
    await _push_config_change("watchlist:deleted")
    return {"status": "ok", "message": f"股票 {code} 已从自选股中移除"}


# ─── 监控池接口 ──────────────────────────────────────

@router.get("/config/monitor")
async def get_monitor_pool(db: AsyncSession = Depends(get_db), request: Request = None):
    """获取监控池标的列表（按用户隔离）。"""
    uid = _get_user_id(request)
    result = await db.execute(
        select(MonitorItem)
        .where(MonitorItem.is_active == True, MonitorItem.user_id == uid)
        .order_by(MonitorItem.id)
    )
    items = result.scalars().all()
    
    # 清理同一(code, user_id)的重复记录，只保留第一条
    seen_codes = {}
    cleaned = []
    for item in items:
        key = (item.code, item.user_id)
        if key in seen_codes:
            item.is_active = False  # 多余的软删除
            continue
        seen_codes[key] = True
        cleaned.append(item)
    if len(cleaned) < len(items):
        await db.commit()
        logger.info(f"监控池读取时清理了 {len(items) - len(cleaned)} 条重复")
    
    output = []
    for item in cleaned:
        name = item.name
        if not name or name == item.code or len(name) <= 2:
            resolved = await resolve_stock_name(item.code)
            if resolved and resolved != item.code:
                name = resolved
                item.name = name
                try:
                    await db.commit()
                except Exception:
                    pass
        output.append({
            "id": item.id,
            "code": item.code,
            "name": name,
            "monitor_type": item.monitor_type,
            "threshold_high": item.threshold_high,
            "threshold_low": item.threshold_low,
            "is_active": item.is_active,
        })
    return output


@router.post("/config/monitor")
async def add_monitor_item(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """添加监控标的（按用户隔离）。"""
    uid = _get_user_id(request)
    code = data.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")

    # 检查是否已存在（仅当前用户，兼容重复记录）
    result = await db.execute(
        select(MonitorItem).where(MonitorItem.code == code, MonitorItem.user_id == uid)
    )
    existing_items = result.scalars().all()
    
    # 清理软删除的重复记录
    active_items = [it for it in existing_items if it.is_active]
    inactive_items = [it for it in existing_items if not it.is_active]
    
    if active_items:
        raise HTTPException(status_code=409, detail=f"股票 {code} 已在监控池中")
    
    # 有软删除的记录：复活其中一条，删除其余的
    if inactive_items:
        primary = inactive_items[0]
        primary.is_active = True
        name = data.get("name", "").strip()
        if not name or name == code or len(name) <= 2:
            resolved = await resolve_stock_name(code)
            if resolved and resolved != code:
                name = resolved
        primary.name = name
        primary.monitor_type = data.get("monitor_type", primary.monitor_type)
        if "threshold_high" in data:
            primary.threshold_high = data["threshold_high"]
        if "threshold_low" in data:
            primary.threshold_low = data["threshold_low"]
        # 删除多余的软删除记录
        for extra in inactive_items[1:]:
            await db.delete(extra)
        await db.commit()
        await _push_config_change("monitor:added")
        return {"status": "ok", "message": f"股票 {code} 已重新加入监控池", "id": primary.id}

    # 获取股票名称
    name = data.get("name", "").strip()
    if not name or name == code or len(name) <= 2:
        resolved = await resolve_stock_name(code)
        if resolved and resolved != code:
            name = resolved

    item = MonitorItem(
        code=code, user_id=uid,
        name=name,
        monitor_type=data.get("monitor_type", "all"),
        threshold_high=data.get("threshold_high"),
        threshold_low=data.get("threshold_low"),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    await _push_config_change("monitor:added")

    return {"status": "ok", "message": f"股票 {code} 已加入监控池", "id": item.id}


@router.put("/config/monitor/{code}")
async def update_monitor_item(
    code: str,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """更新监控标的配置（兼容重复记录）。"""
    uid = _get_user_id(request)
    result = await db.execute(
        select(MonitorItem).where(MonitorItem.code == code, MonitorItem.user_id == uid)
    )
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不在监控池中")

    primary = items[0]
    if "name" in data:
        primary.name = data["name"]
    if "monitor_type" in data:
        primary.monitor_type = data["monitor_type"]
    if "threshold_high" in data:
        primary.threshold_high = data["threshold_high"]
    if "threshold_low" in data:
        primary.threshold_low = data["threshold_low"]
    # 清理多余的重复记录
    for extra in items[1:]:
        await db.delete(extra)
    if "is_active" in data:
        item.is_active = data["is_active"]

    await db.commit()
    await _push_config_change("monitor:updated")
    return {"status": "ok", "message": f"股票 {code} 监控配置已更新"}


@router.delete("/config/monitor/{code}")
async def delete_monitor_item(code: str, db: AsyncSession = Depends(get_db), request: Request = None):
    """删除监控标的（软删除）。处理重复记录情况。"""
    uid = _get_user_id(request)
    result = await db.execute(
        select(MonitorItem).where(MonitorItem.code == code, MonitorItem.user_id == uid)
    )
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不在监控池中")

    count = 0
    for item in items:
        if item.is_active:
            item.is_active = False
            count += 1
    await db.commit()
    await _push_config_change("monitor:deleted")
    extra = f"（清理了 {len(items)} 条重复记录）" if len(items) > 1 else ""
    return {"status": "ok", "message": f"股票 {code} 已从监控池移除{extra}"}


# ─── 数据源管理接口 ──────────────────────────────────

@router.get("/config/datasource")
async def get_datasource_status(
    db: AsyncSession = Depends(get_db),
):
    """获取数据源状态列表（含自定义数据源）。"""
    try:
        dsm = _get_dsm()
        sources = dsm.get_status_summary()

        # 合并自定义数据源
        from backend.models.config import CustomDataSource
        result = await db.execute(
            select(CustomDataSource).order_by(CustomDataSource.id)
        )
        custom_items = result.scalars().all()
        for item in custom_items:
            sources.append({
                "name": item.name,
                "type": "custom",
                "status": "online" if item.enabled else "offline",
                "latency": 0,
                "description": item.description or f"自定义数据源: {item.api_url}",
                "is_primary": False,
            })

        return {
            "sources": sources,
            "active_source": dsm._active_name,
            "primary_source": dsm._primary_name,
            "fallback_source": dsm._fallback_name,
            "tdx_enabled": settings.tdx_enabled,
            "module_mapping": dsm.MODULE_SOURCES,
            "custom_sources": [
                {
                    "id": item.id,
                    "name": item.name,
                    "api_url": item.api_url,
                    "enabled": item.enabled,
                    "description": item.description,
                }
                for item in custom_items
            ],
        "tdx_enabled": settings.tdx_enabled,
            "module_mapping": dsm.MODULE_SOURCES,
        }
    except Exception as e:
        logger.error(f"获取数据源状态失败: {e}")
        return {
            "sources": [],
            "active_source": None,
            "primary_source": settings.primary_data_source,
            "fallback_source": settings.fallback_data_source,
            "tdx_enabled": settings.tdx_enabled,
            "module_mapping": {},
        }


@router.post("/config/datasource/switch")
async def switch_datasource(
    data: Dict[str, Any] = Body(...),
):
    """
    手动切换活跃数据源。
    请求体：{"id": "sina"} 或 {"source_name": "sina"}
    """
    source_name = data.get("source_name", "") or data.get("id", "")
    source_name = source_name.strip()
    if not source_name:
        raise HTTPException(status_code=400, detail="数据源名称不能为空")

    try:
        dsm = _get_dsm()
        if source_name not in dsm._sources:
            raise HTTPException(status_code=404, detail=f"数据源 {source_name} 未注册")

        source = dsm._sources[source_name]
        if not source.is_available():
            raise HTTPException(status_code=400, detail=f"数据源 {source_name} 当前不可用")

        dsm._active_name = source_name
        await _push_config_change(f"datasource:switched_to_{source_name}")
        return {
            "status": "ok",
            "message": f"已切换至数据源 {source_name}",
            "active_source": source_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换数据源失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换数据源失败: {str(e)}")


@router.post("/config/datasource/test")
async def test_datasource_connection(
    data: Dict[str, Any] = Body(...),
):
    """
    测试数据源连通性。
    请求体：{"id": "sina"} 或 {"source_name": "sina"}
    """
    source_name = data.get("id", "") or data.get("source_name", "")
    source_name = source_name.strip()
    if not source_name:
        raise HTTPException(status_code=400, detail="数据源名称不能为空")

    # 统一名称（前端 tdx → tdx_local）
    backend_name = {
        "tdx": "tdx_local",
        "eastmoney": "eastmoney",
    }.get(source_name, source_name)

    try:
        dsm = _get_dsm()
        import time
        start = time.time()
        # 调用数据源的 ping 或简单查询来测试连通性
        if backend_name in dsm._sources:
            source = dsm._sources[backend_name]
            try:
                data = await source.get_quotes(["000001"])
                latency = int((time.time() - start) * 1000)
                source._status = "online"
                source._consecutive_failures = 0
                return {
                    "status": "ok",
                    "latency": latency,
                    "message": f"数据源 {source_name} 连接正常"
                }
            except Exception as e:
                source._status = "offline"
                source._consecutive_failures += 1
                return {
                    "status": "error",
                    "latency": int((time.time() - start) * 1000),
                    "message": f"数据源 {source_name} 连接失败: {str(e)}"
                }
        else:
            raise HTTPException(status_code=404, detail=f"数据源 {source_name} 未注册")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试连接失败: {str(e)}")


@router.post("/config/datasource/reset")
async def reset_data_sources():
    """重置所有数据源的状态。清空失败计数、恢复ONLINE。"""
    try:
        dsm = _get_dsm()
        dsm.reset_source_status()
        dsm._active_name = dsm._primary_name
        await _push_config_change("datasource:reset")
        return {"status": "ok", "message": "所有数据源状态已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置数据源失败: {str(e)}")


# ─── 模板管理接口 ──────────────────────────────────────

TEMPLATES_DIR = os.path.join(".", "data", "templates")

# 知识库模板文件路径
KB_TEMPLATES = [
    ("premarket", r"C:\openclaw-docs\股票分析与投资决策系统设计文档\A股市场盘前提示模板.md"),
    ("selection", r"C:\openclaw-docs\股票分析与投资决策系统设计文档\A股个股_批量股票分析模板.md"),
    ("analysis", r"C:\openclaw-docs\股票分析与投资决策系统设计文档\A股市场每日复盘分析模板.md"),
]

DEFAULT_TEMPLATE_FILE = os.path.join(TEMPLATES_DIR, ".default_template")


def _user_templates_dir(uid=1):
    d = os.path.join(TEMPLATES_DIR, "user_%d" % uid)
    os.makedirs(d, exist_ok=True)
    return d


def _ensure_templates_dir(uid=1):
    """确保模板目录存在，并从知识库拷贝默认模板"""
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    for ttype, src_path in KB_TEMPLATES:
        if not os.path.isfile(src_path):
            continue
        dst_name = os.path.basename(src_path)
        dst_path = os.path.join(TEMPLATES_DIR, dst_name)
        if not os.path.isfile(dst_path):
            try:
                import shutil
                shutil.copy2(src_path, dst_path)
                logger.info(f"模板已导入：{dst_name}")
            except Exception as e:
                logger.warning(f"模板导入失败 {dst_name}: {e}")


# 各类默认模板文件名后缀（按模块用途区分）
_DEFAULT_FILE_SUFFIX = {
    "premarket": "_premarket",
    "review": "_review",
    "batch": "_batch",
    "stock": "_stock",
    "selection": "_selection",
}


def _default_file_for(template_type: str = "") -> str:
    """获取指定类型的默认模板标记文件名"""
    suffix = _DEFAULT_FILE_SUFFIX.get(template_type, "")
    return os.path.join(TEMPLATES_DIR, f".default_template{suffix}")


def resolve_template_path(template_type: str = "") -> str | None:
    """
    根据类型和默认模板设置解析模板文件完整路径。
    先查类型专属默认（如 .default_template_review），再查全局默认。
    
    Args:
        template_type: 模板用途类型: premarket/review/batch/stock/selection
    Returns:
        模板文件完整路径，无可用的模板时返回 None
    """
    for df in [_default_file_for(template_type), DEFAULT_TEMPLATE_FILE]:
        try:
            if os.path.isfile(df):
                with open(df, "r", encoding="utf-8") as f:
                    name = f.read().strip()
                    if name:
                        path = os.path.join(TEMPLATES_DIR, name)
                        if os.path.isfile(path):
                            return os.path.abspath(path)
        except Exception:
            pass
    return None


def _get_type_defaults() -> dict:
    """读取所有类型专属的默认模板名称"""
    result = {}
    for ttype in _DEFAULT_FILE_SUFFIX:
        df = _default_file_for(ttype)
        try:
            if os.path.isfile(df):
                with open(df, "r", encoding="utf-8") as f:
                    name = f.read().strip()
                    if name:
                        result[ttype] = name
        except Exception:
            pass
    return result


def _get_default_template_name() -> str:
    """获取全局默认模板名称（兼容旧版）"""
    try:
        if os.path.isfile(DEFAULT_TEMPLATE_FILE):
            with open(DEFAULT_TEMPLATE_FILE, "r", encoding="utf-8") as f:
                name = f.read().strip()
                if name and os.path.isfile(os.path.join(TEMPLATES_DIR, name)):
                    return name
    except Exception:
        pass
    for ttype, src_path in KB_TEMPLATES:
        if ttype == "premarket":
            return os.path.basename(src_path)
    return ""


def _set_default_template_name(name: str):
    """设置默认模板名称"""
    try:
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        with open(DEFAULT_TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except Exception as e:
        logger.warning(f"设置默认模板失败: {e}")


@router.get("/config/templates")
async def get_templates(template_type: str = Query("", description="模板类型：analysis/selection/premarket")):
    """获取模板列表。按类型筛选，返回含 is_default 标记。"""
    _ensure_templates_dir()
    default_name = _get_default_template_name()
    type_defaults = _get_type_defaults()
    templates = []
    try:
        for filename in os.listdir(TEMPLATES_DIR):
            if not filename.endswith((".json", ".md")):
                continue
            if filename.startswith("."):
                continue
            filepath = os.path.join(TEMPLATES_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            stat = os.stat(filepath)
            # 从文件名推断类型
            fname_lower = filename.lower()
            detected_type = "analysis"
            if "选股" in fname_lower or "selection" in fname_lower:
                detected_type = "selection"
            elif "盘前" in fname_lower or "premarket" in fname_lower:
                detected_type = "premarket"
            elif "复盘" in fname_lower or "review" in fname_lower or "daily" in fname_lower:
                detected_type = "analysis"

            if template_type and detected_type != template_type:
                continue

            # 判断该模板是哪种用途的默认模板
            is_global_default = filename == default_name
            per_type_defaults = []
            for ttype, tname in type_defaults.items():
                if tname == filename:
                    per_type_defaults.append(ttype)

            templates.append({
                "id": filename,
                "name": filename.replace(".md", "").replace(".json", ""),
                "type": detected_type,
                "filename": filename,
                "size": stat.st_size,
                "is_default": is_global_default,
                "defaults_for": per_type_defaults,  # 如 ["review", "batch"]
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    except FileNotFoundError:
        pass

    templates.sort(key=lambda t: (not t["is_default"], t["name"]))
    return {"templates": templates, "template_type": template_type or "all",
            "default": default_name, "type_defaults": type_defaults}


@router.get("/config/templates/{name}")
async def get_template_content(name: str, request: Request = None):
    """获取指定模板内容。"""
    uid = _get_user_id(request)
    filepath = os.path.join(TEMPLATES_DIR, name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"模板 {name} 不存在")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"name": name, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取模板失败: {str(e)}")


@router.post("/config/templates")
async def save_template(
    data: Dict[str, Any] = Body(...),
    request: Request = None,
):
    """
    保存模板。
    请求体：{"name": "daily_review.md", "content": "# 复盘报告...", "overwrite": true}
    """
    name = data.get("name", "").strip()
    content = data.get("content", "")
    overwrite = data.get("overwrite", True)

    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")

    uid = _get_user_id(request)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    filepath = os.path.join(TEMPLATES_DIR, name)

    if os.path.isfile(filepath) and not overwrite:
        raise HTTPException(status_code=409, detail=f"模板 {name} 已存在，请设置 overwrite=true 覆盖")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        await _push_config_change(f"template:saved_{name}")
        return {"status": "ok", "message": f"模板 {name} 已保存"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存模板失败: {str(e)}")


@router.put("/config/templates/{name}/default")
async def set_default_template(
    name: str,
    template_type: str = Query("", description="模板用途类型: premarket/review/batch/stock/selection"),
    request: Request = None,
):
    """
    设为默认模板。
    
    支持按用途类型分别设置默认：
    - template_type=review  → 写 .default_template_review（复盘分析）
    - template_type=batch   → 写 .default_template_batch（批量分析）
    - template_type=stock   → 写 .default_template_stock（个股分析）
    - template_type=premarket → 写 .default_template_premarket（盘前提示）
    - 空字符串 → 写 .default_template（全局默认，向后兼容）
    """
    uid = _get_user_id(request)
    filepath = os.path.join(TEMPLATES_DIR, name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"模板 {name} 不存在")
    if template_type:
        df = _default_file_for(template_type)
        try:
            os.makedirs(os.path.dirname(df), exist_ok=True)
            with open(df, "w", encoding="utf-8") as f:
                f.write(name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"设置默认模板失败: {str(e)}")
    else:
        _set_default_template_name(name)
    await _push_config_change(f"template:default_{template_type}_{name}")
    return {"status": "ok", "message": f"模板 {name} 已设为{template_type or '全局'}默认"}


@router.delete("/config/templates/{name}")
async def delete_template(name: str, request: Request = None):
    """删除模板。"""
    uid = _get_user_id(request)
    filepath = os.path.join(TEMPLATES_DIR, name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"模板 {name} 不存在")
    try:
        os.remove(filepath)
        await _push_config_change(f"template:deleted_{name}")
        return {"status": "ok", "message": f"模板 {name} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")


@router.get("/config/templates/{name}/export")
async def export_template(name: str, request: Request = None):
    """导出模板为文本文件。"""
    uid = _get_user_id(request)
    filepath = os.path.join(TEMPLATES_DIR, name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"模板 {name} 不存在")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        from urllib.parse import quote
        # RFC 5987: 中文文件名用 filename* UTF-8 编码，避免 latin-1 报错
        safe_name = name.replace(".md", "").replace(".json", "")
        utf8_name = quote(safe_name + '.md', safe='')  # 中文 → percent-encoded
        return PlainTextResponse(content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{utf8_name}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出模板失败: {str(e)}")


@router.post("/config/templates/import")
async def import_template(
    data: Dict[str, Any] = Body(...),
    request: Request = None,
):
    """
    导入模板。
    请求体：{"name": "my_template.md", "content": "# 我的模板..."}
    """
    name = data.get("name", "").strip()
    content = data.get("content", "")
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")
    if not name.endswith((".md", ".json")):
        name += ".md"
    uid = _get_user_id(request)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    filepath = os.path.join(TEMPLATES_DIR, name)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        await _push_config_change(f"template:imported_{name}")
        return {"status": "ok", "message": f"模板 {name} 已导入", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入模板失败: {str(e)}")


# ─── 用户偏好接口 ──────────────────────────────────────

@router.get("/config/preferences")
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """获取所有用户偏好设置。"""
    result = await db.execute(select(UserPreference))
    preferences = {}
    for pref in result.scalars().all():
        # 尝试解析JSON值
        try:
            preferences[pref.key] = json.loads(pref.value)
        except (json.JSONDecodeError, TypeError):
            preferences[pref.key] = pref.value
    return {"preferences": preferences}


@router.put("/config/preferences")
async def update_preferences(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    更新用户偏好。
    请求体：{"theme": "dark", "refresh_interval": 5, ...}
    """
    updated_keys = []
    for key, value in data.items():
        value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        stmt = select(UserPreference).where(UserPreference.key == key)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value_str
        else:
            db.add(UserPreference(key=key, value=value_str, description=""))
        updated_keys.append(key)

    await db.commit()
    await _push_config_change("preferences:updated")
    return {
        "status": "ok",
        "message": f"偏好已更新: {', '.join(updated_keys)}",
        "updated_keys": updated_keys,
    }


@router.get("/config/preferences/{key}")
async def get_preference(key: str, db: AsyncSession = Depends(get_db)):
    """获取单个偏好值。"""
    result = await db.execute(
        select(UserPreference).where(UserPreference.key == key)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise HTTPException(status_code=404, detail=f"偏好 {key} 不存在")
    try:
        value = json.loads(pref.value)
    except (json.JSONDecodeError, TypeError):
        value = pref.value
    return {"key": key, "value": value}


# ─── 系统状态接口 ──────────────────────────────────────

@router.get("/system/status")
@router.get("/config/system")
async def get_system_status():
    """获取系统状态信息。"""
    import platform
    import psutil

    try:
        # 系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(".")

        # 数据源状态
        try:
            dsm = _get_dsm()
            data_sources = dsm.get_status_summary()
            active_source = dsm._active_name
        except Exception:
            data_sources = []
            active_source = "unknown"

        # 数据库状态（检查数据量）
        db_size = 0
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        if os.path.isfile(db_path):
            db_size = os.path.getsize(db_path)

        return {
            "system": {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available_mb": round(memory.available / 1024 / 1024, 1),
                "disk_usage": disk.percent,
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            },
            "application": {
                "version": "1.0.0",
                "backend_host": settings.backend_host,
                "backend_port": settings.backend_port,
                "uptime": None,  # TODO: 记录启动时间
            },
            "database": {
                "path": db_path,
                "size_bytes": db_size,
                "size_mb": round(db_size / 1024 / 1024, 2) if db_size > 0 else 0,
            },
            "data_sources": data_sources,
            "active_source": active_source,
            "module_mapping": dsm.MODULE_SOURCES if active_source != "unknown" else {},
        }
    except ImportError:
        # psutil 未安装，返回基本信息
        return {
            "system": {
                "platform": platform.platform(),
                "note": "psutil未安装，详细系统信息不可用",
            },
            "data_sources": [],
            "active_source": "unknown",
        }
    except Exception as e:
        logger.error(f"获取系统状态异常: {e}")
        return {
            "system": {"error": str(e)},
            "data_sources": [],
            "active_source": "unknown",
        }


# ─── 批量同步接口 ──────────────────────────────────────

@router.post("/config/watchlist/sync")
async def sync_watchlist(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    批量同步自选股（全量替换）。
    请求体：{"items": [{"code": "000001", "name": "平安银行", "sort_order": 0}, ...]}
    """
    items = data.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items 必须是数组")

    # 软删除当前所有自选股
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.is_active == True)
    )
    for item in result.scalars().all():
        item.is_active = False

    # 添加新列表
    added = []
    for idx, item_data in enumerate(items):
        code = item_data.get("code", "").strip()
        if not code:
            continue
        existing = await db.execute(
            select(WatchlistItem).where(WatchlistItem.code == code)
        )
        existing_item = existing.scalar_one_or_none()
        if existing_item:
            existing_item.is_active = True
            existing_item.name = item_data.get("name", existing_item.name)
            existing_item.sort_order = item_data.get("sort_order", idx)
            existing_item.added_reason = item_data.get("added_reason", existing_item.added_reason)
        else:
            db.add(WatchlistItem(
                code=code,
                name=item_data.get("name", ""),
                sort_order=item_data.get("sort_order", idx),
                added_reason=item_data.get("added_reason", ""),
            ))
        added.append(code)

    await db.commit()
    await _push_config_change("watchlist:synced")
    return {"status": "ok", "message": f"自选股已同步，共 {len(added)} 只", "count": len(added)}


@router.post("/config/monitor/sync")
async def sync_monitor_pool(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    批量同步监控池（全量替换）。
    请求体：{"items": [{"code": "000001", "name": "平安银行", "monitor_type": "all"}, ...]}
    """
    items = data.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items 必须是数组")

    # 软删除当前所有监控标的
    result = await db.execute(
        select(MonitorItem).where(MonitorItem.is_active == True)
    )
    for item in result.scalars().all():
        item.is_active = False

    added = []
    for item_data in items:
        code = item_data.get("code", "").strip()
        if not code:
            continue
        if code in added:
            continue  # 去重：同一批次中重复的跳过
        existing = await db.execute(
            select(MonitorItem).where(MonitorItem.code == code)
        )
        existing_items = existing.scalars().all()
        if existing_items:
            # 复活第一个，删除多余的
            primary = existing_items[0]
            primary.is_active = True
            primary.name = item_data.get("name", primary.name)
            primary.monitor_type = item_data.get("monitor_type", primary.monitor_type)
            for extra in existing_items[1:]:
                await db.delete(extra)
        else:
            db.add(MonitorItem(
                code=code,
                name=item_data.get("name", ""),
                monitor_type=item_data.get("monitor_type", "all"),
            ))
        added.append(code)

    await db.commit()
    await _push_config_change("monitor:synced")
    return {"status": "ok", "message": f"监控池已同步，共 {len(added)} 只", "count": len(added)}


# ─── 通达信自选股导入 ────────────────────────────────

@router.post("/config/watchlist/import-tdx")
async def import_tdx_watchlist(
    db: AsyncSession = Depends(get_db),
):
    """
    从中信证券通达信 ZXG.blk 文件一键导入自选股。
    文件格式：每行 1 位市场码 + 6 位股票代码（GBK编码）。
    市场码：0=深市, 1=沪市, 2=北交所
    文件路径：C:/zd_zxzq_gm/T0002/blocknew/ZXG.blk
    """
    tdx_path = r"C:\zd_zxzq_gm\T0002\blocknew\ZXG.blk"

    if not os.path.exists(tdx_path):
        raise HTTPException(status_code=404, detail=f"通达信自选股文件不存在: {tdx_path}")

    try:
        with open(tdx_path, "rb") as f:
            raw = f.read()
        text = raw.decode("gbk", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取自选股文件失败: {e}")

    # 解析每行：市场码(1位) + 代码(6位)
    imported = []
    skipped_duplicates = 0
    skipped_invalid = 0

    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 7:
            continue

        market_code = line[0]  # 0=SZ, 1=SH, 2=BJ
        stock_code = line[1:7].strip()

        if not stock_code.isdigit() or len(stock_code) != 6:
            skipped_invalid += 1
            continue

        # 检查是否已存在
        result = await db.execute(
            select(WatchlistItem).where(WatchlistItem.code == stock_code)
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.is_active:
                skipped_duplicates += 1
                continue
            # 重新激活软删除的
            existing.is_active = True
            await db.commit()
            imported.append(stock_code)
            continue

        # 查询股票名称
        name = await resolve_stock_name(stock_code)
        if not name:
            name = stock_code

        db.add(WatchlistItem(
            code=stock_code,
            name=name,
            added_reason="从通达信自选股导入",
        ))
        imported.append(stock_code)

    await db.commit()
    await _push_config_change("watchlist:synced")

    return {
        "status": "ok",
        "message": f"成功导入 {len(imported)} 只股票" +
                   (f"，{skipped_duplicates} 只已存在已跳过" if skipped_duplicates else "") +
                   (f"，{skipped_invalid} 行格式无效" if skipped_invalid else ""),
        "imported": imported,
        "skipped_duplicates": skipped_duplicates,
        "skipped_invalid": skipped_invalid,
    }
