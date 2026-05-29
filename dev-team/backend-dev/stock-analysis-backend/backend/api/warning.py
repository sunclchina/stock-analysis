"""
M03 智能预警模块API — 完整实现。

遵循架构方案4.1节 M03 预警接口定义：
- GET    /api/v1/warning/list           → 预警列表（带分页/过滤）
- GET    /api/v1/warning/summary        → 预警汇总
- PUT    /api/v1/warning/{id}/ack       → 标记预警已处理
- GET    /api/v1/warning/{code}/detail  → 单只股票预警详情
- PUT    /api/v1/warning/{code}/resolve → 主动解除预警

阶段3完整实现，支持7种预警类型和综合决策矩阵。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select, delete, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.warning import WarningRecord, WarningConfig
from backend.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["warning"], prefix="/warning")

# 延迟引用
_warning_engine = None


def _get_engine():
    global _warning_engine
    if _warning_engine is None:
        from backend.main import warning_engine
        _warning_engine = warning_engine
    return _warning_engine


# ─── 预警列表 ─────────────────────────────────────────

@router.get("/list")
async def get_warning_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    warning_type: str = Query("", description="预警类型过滤：price/updown/trend/resonance/finance/event/risk/decision"),
    level: str = Query("", description="级别过滤：info/warning/danger/critical"),
    color: str = Query("", description="颜色过滤：gray/green/yellow/red/purple"),
    acknowledged: Optional[bool] = Query(None, description="处理状态：true=已处理/false=未处理"),
    code: str = Query("", description="股票代码过滤"),
    sort_by: str = Query("triggered_at", description="排序字段：triggered_at/level/type"),
    sort_order: str = Query("desc", description="排序方向：asc/desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    预警列表（带分页和多种过滤条件）。
    
    支持按类型、级别、颜色、处理状态、股票代码过滤。
    """
    # 基础查询
    stmt = select(WarningRecord)

    # 过滤条件
    if warning_type:
        stmt = stmt.where(WarningRecord.warning_type == warning_type)
    if level:
        stmt = stmt.where(WarningRecord.warning_level == level)
    if color:
        stmt = stmt.where(WarningRecord.indicator_color == color)
    if acknowledged is not None:
        stmt = stmt.where(WarningRecord.is_acknowledged == acknowledged)
    if code:
        stmt = stmt.where(WarningRecord.code == code)

    # 计数
    count_stmt = select(sa_func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 排序
    sort_column = getattr(WarningRecord, sort_by, WarningRecord.triggered_at)
    if sort_order == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "items": [r.to_dict() for r in records],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


# ─── 预警汇总 ─────────────────────────────────────────

@router.get("/summary")
async def get_warning_summary(db: AsyncSession = Depends(get_db)):
    """
    预警汇总统计。
    
    按类型和级别分别统计未处理预警数量。
    """
    # 按类型统计
    type_stmt = (
        select(
            WarningRecord.warning_type,
            sa_func.count(WarningRecord.id)
        )
        .where(WarningRecord.is_acknowledged == False)
        .group_by(WarningRecord.warning_type)
    )
    type_result = await db.execute(type_stmt)
    by_type = {}
    for row in type_result.all():
        by_type[row.warning_type] = row[1]

    # 按级别统计
    level_stmt = (
        select(
            WarningRecord.warning_level,
            sa_func.count(WarningRecord.id)
        )
        .where(WarningRecord.is_acknowledged == False)
        .group_by(WarningRecord.warning_level)
    )
    level_result = await db.execute(level_stmt)
    by_level = {}
    for row in level_result.all():
        by_level[row.warning_level] = row[1]

    # 按颜色统计
    color_stmt = (
        select(
            WarningRecord.indicator_color,
            sa_func.count(WarningRecord.id)
        )
        .where(WarningRecord.is_acknowledged == False)
        .group_by(WarningRecord.indicator_color)
    )
    color_result = await db.execute(color_stmt)
    by_color = {}
    for row in color_result.all():
        by_color[row.indicator_color] = row[1]

    # 总计数
    total_result = await db.execute(
        select(sa_func.count(WarningRecord.id))
        .where(WarningRecord.is_acknowledged == False)
    )
    total = total_result.scalar() or 0

    # 映射级别到前端兼容格式（info→low, warning→medium, danger→high, critical→high）
    level_map = {"info": "low", "warning": "medium", "danger": "high", "critical": "high"}
    by_level_frontend = {}
    for k, v in by_level.items():
        mapped = level_map.get(k, k)
        by_level_frontend[mapped] = by_level_frontend.get(mapped, 0) + v

    return {
        "total": total,
        "unprocessed": total,
        "by_type": by_type,
        "by_level": by_level_frontend,
        "by_color": by_color,
        "timestamp": datetime.now().isoformat(),
    }


# ─── 标记处理 ─────────────────────────────────────────

@router.put("/{warning_id}/ack")
async def acknowledge_warning(
    warning_id: int,
    data: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db),
):
    """标记预警已处理。"""
    result = await db.execute(
        select(WarningRecord).where(WarningRecord.id == warning_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"预警记录 {warning_id} 不存在")

    record.is_acknowledged = True
    record.acknowledged_at = datetime.now()
    await db.commit()

    # 推送预警解除事件
    try:
        await ws_manager.broadcast_warning_resolve(str(warning_id))
    except Exception as e:
        logger.warning(f"WebSocket推送预警解除失败: {e}")

    return {
        "status": "ok",
        "id": warning_id,
        "message": f"预警 {warning_id} 已标记为已处理",
    }


# ─── 批量标记处理 ────────────────────────────────────

@router.put("/batch/ack")
async def batch_acknowledge(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    批量标记预警已处理。
    请求体：{"ids": [1, 2, 3]} 或 {"code": "000001", "warning_type": "trend"}
    """
    ids = data.get("ids", [])
    code = data.get("code", "")
    warning_type = data.get("warning_type", "")

    stmt = select(WarningRecord)

    if ids:
        stmt = stmt.where(WarningRecord.id.in_(ids))
    elif code:
        stmt = stmt.where(WarningRecord.code == code)
        if warning_type:
            stmt = stmt.where(WarningRecord.warning_type == warning_type)
    else:
        raise HTTPException(status_code=400, detail="请提供 ids 或 code 参数")

    result = await db.execute(stmt)
    records = result.scalars().all()
    now = datetime.now()

    ack_count = 0
    for r in records:
        if not r.is_acknowledged:
            r.is_acknowledged = True
            r.acknowledged_at = now
            ack_count += 1

    await db.commit()

    return {
        "status": "ok",
        "acknowledged_count": ack_count,
        "message": f"已处理 {ack_count} 条预警记录",
    }


# ─── 单只股票预警详情 ────────────────────────────────

@router.get("/{code}/detail")
async def get_warning_detail(
    code: str,
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    db: AsyncSession = Depends(get_db),
):
    """
    单只股票预警详情。
    
    返回该股票的所有预警类型记录、当前预警引擎状态和综合颜色。
    """
    # 从数据库获取历史预警记录
    stmt = (
        select(WarningRecord)
        .where(WarningRecord.code == code)
        .order_by(WarningRecord.triggered_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    # 统计未处理预警
    unack_count = sum(1 for r in records if not r.is_acknowledged)

    # 获取预警引擎当前颜色状态
    engine = _get_engine()
    current_colors = {}
    if engine and hasattr(engine, '_previous_colors'):
        for key, color in engine._previous_colors.items():
            if key.startswith(f"{code}:"):
                wtype = key.split(":", 1)[1] if ":" in key else ""
                current_colors[wtype] = color

    # 计算最高颜色
    color_priority = {"gray": 0, "green": 1, "yellow": 2, "red": 3, "purple": 4}
    current_level = max(current_colors.values(), key=lambda c: color_priority.get(c, 0)) if current_colors else "gray"

    return {
        "code": code,
        "warnings": [r.to_dict() for r in records],
        "total": len(records),
        "unacknowledged": unack_count,
        "current_colors": current_colors,
        "current_level": current_level,
    }


# ─── 主动解除预警 ────────────────────────────────────

@router.put("/{code}/resolve")
async def resolve_warning(
    code: str,
    data: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db),
):
    """
    主动解除某只股票的全部或指定类型预警。
    请求体：{"warning_type": "trend"} 可选，不传则解除全部类型
    """
    warning_type = data.get("warning_type", "")

    # 解除预警引擎状态
    engine = _get_engine()
    if engine and hasattr(engine, '_previous_colors'):
        if warning_type:
            await engine.resolve_warning(code, warning_type)
        else:
            # 解除该股票所有类型
            for key in list(engine._previous_colors.keys()):
                if key.startswith(f"{code}:"):
                    wtype = key.split(":", 1)[1] if ":" in key else ""
                    await engine.resolve_warning(code, wtype)

    # 标记数据库中的记录
    stmt = select(WarningRecord).where(
        WarningRecord.code == code,
        WarningRecord.is_acknowledged == False,
    )
    if warning_type:
        stmt = stmt.where(WarningRecord.warning_type == warning_type)

    result = await db.execute(stmt)
    records = result.scalars().all()
    now = datetime.now()

    for r in records:
        r.is_acknowledged = True
        r.acknowledged_at = now

    await db.commit()

    resolve_type = warning_type if warning_type else "all"
    return {
        "status": "ok",
        "code": code,
        "resolve_type": resolve_type,
        "resolved_count": len(records),
        "message": f"股票 {code} 的 {resolve_type} 预警已解除",
    }


# ─── 预警配置管理 ─────────────────────────────────────

@router.get("/config/list")
async def get_warning_configs(db: AsyncSession = Depends(get_db)):
    """获取预警规则配置列表"""
    result = await db.execute(
        select(WarningConfig)
        .where(WarningConfig.is_active == True)
        .order_by(WarningConfig.config_type, WarningConfig.code)
    )
    configs = result.scalars().all()
    return {
        "items": [c.to_dict() for c in configs],
        "total": len(configs),
    }


@router.post("/config/update")
async def update_warning_config(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    更新预警规则配置。
    请求体：{"config_type": "trend", "code": "000001", "params": {"ma_deviation_threshold": 0.03}}
    code 为空时为全局配置。
    """
    config_type = data.get("config_type", "")
    code = data.get("code")
    params = data.get("params", {})
    description = data.get("description", "")

    if not config_type:
        raise HTTPException(status_code=400, detail="config_type 不能为空")

    stmt = select(WarningConfig).where(
        WarningConfig.config_type == config_type,
        WarningConfig.code == code if code else WarningConfig.code.is_(None),
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.params = params
        if description:
            config.description = description
    else:
        config = WarningConfig(
            config_type=config_type,
            code=code,
            params=params,
            description=description,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return {"status": "ok", "message": f"{config_type} 预警配置已更新", "config": config.to_dict()}
