"""
自定义数据源管理 API（付费第三方数据源）。

提供完整 CRUD 与连通性测试功能：
- GET    /api/v1/config/custom-datasource       → 列表查询
- POST   /api/v1/config/custom-datasource       → 新增
- PUT    /api/v1/config/custom-datasource/{id}  → 更新
- DELETE /api/v1/config/custom-datasource/{id}  → 删除
- POST   /api/v1/config/custom-datasource/test  → 连通性测试

API密钥存储前做 Base64 编码，避免明文入库。
"""

import base64
import logging
from typing import Any, Dict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.config import CustomDataSource

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])


def _encode_key(key: str) -> str:
    """API密钥 Base64 编码存储"""
    return base64.b64encode(key.encode("utf-8")).decode("utf-8")


def _decode_key(encoded: str) -> str:
    """解码存储的 API 密钥"""
    try:
        return base64.b64decode(encoded.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _to_dict(item: CustomDataSource, mask_key: bool = True) -> Dict[str, Any]:
    """将模型转为字典，默认掩码 API 密钥"""
    return {
        "id": item.id,
        "name": item.name,
        "api_url": item.api_url,
        "api_key": "***masked***" if mask_key else _decode_key(item.api_key),
        "description": item.description or "",
        "enabled": item.enabled,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


# ─── 列表查询 ──────────────────────────────────────

@router.get("/config/custom-datasource")
async def list_custom_datasources(db: AsyncSession = Depends(get_db)):
    """获取所有自定义数据源列表。"""
    result = await db.execute(
        select(CustomDataSource).order_by(CustomDataSource.id)
    )
    items = result.scalars().all()
    return {
        "sources": [_to_dict(item) for item in items],
        "total": len(items),
    }


# ─── 新增 ──────────────────────────────────────────

@router.post("/config/custom-datasource")
async def create_custom_datasource(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """新增自定义数据源。"""
    name = (data.get("name") or "").strip()
    api_url = (data.get("api_url") or "").strip()
    api_key = data.get("api_key") or ""

    if not name:
        raise HTTPException(status_code=400, detail="数据源名称不能为空")
    if not api_url:
        raise HTTPException(status_code=400, detail="API地址不能为空")

    # 检查重名
    result = await db.execute(
        select(CustomDataSource).where(CustomDataSource.name == name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"数据源名称 '{name}' 已存在")

    item = CustomDataSource(
        name=name,
        api_url=api_url,
        api_key=_encode_key(api_key),
        description=(data.get("description") or "").strip(),
        enabled=data.get("enabled", True),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    logger.info(f"新增自定义数据源: {name} (id={item.id})")

    return {
        "status": "ok",
        "message": f"自定义数据源 '{name}' 已创建",
        "data": _to_dict(item),
    }


# ─── 更新 ──────────────────────────────────────────

@router.put("/config/custom-datasource/{id}")
async def update_custom_datasource(
    id: int,
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """更新自定义数据源配置。"""
    result = await db.execute(
        select(CustomDataSource).where(CustomDataSource.id == id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"自定义数据源(id={id}) 不存在")

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="数据源名称不能为空")
        # 查重（排除自身）
        dup = await db.execute(
            select(CustomDataSource).where(
                CustomDataSource.name == name,
                CustomDataSource.id != id,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"数据源名称 '{name}' 已存在")
        item.name = name

    if "api_url" in data:
        url = (data["api_url"] or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="API地址不能为空")
        item.api_url = url

    if "api_key" in data:
        item.api_key = _encode_key(data["api_key"])

    if "description" in data:
        item.description = (data["description"] or "").strip()

    if "enabled" in data:
        item.enabled = data["enabled"]

    await db.commit()
    await db.refresh(item)
    logger.info(f"更新自定义数据源: id={id}")

    return {
        "status": "ok",
        "message": f"自定义数据源 '{item.name}' 已更新",
        "data": _to_dict(item),
    }


# ─── 删除 ──────────────────────────────────────────

@router.delete("/config/custom-datasource/{id}")
async def delete_custom_datasource(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除自定义数据源。"""
    result = await db.execute(
        select(CustomDataSource).where(CustomDataSource.id == id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"自定义数据源(id={id}) 不存在")

    name = item.name
    await db.delete(item)
    await db.commit()
    logger.info(f"删除自定义数据源: {name} (id={id})")

    return {"status": "ok", "message": f"自定义数据源 '{name}' 已删除"}


# ─── 连通性测试 ──────────────────────────────────

@router.post("/config/custom-datasource/test")
async def test_custom_datasource(
    data: Dict[str, Any] = Body(...),
):
    """
    测试自定义数据源连通性。
    请求体：{"api_url": "https://api.example.com/data", "api_key": "your-key"}
    向指定 API 发送 HTTP GET 请求，超时5秒。
    """
    api_url = (data.get("api_url") or "").strip()
    api_key = data.get("api_key") or ""

    if not api_url:
        raise HTTPException(status_code=400, detail="API地址不能为空")

    import time
    import httpx

    start = time.time()
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(api_url, headers=headers)

        elapsed = int((time.time() - start) * 1000)

        if response.status_code < 500:
            return {
                "status": "ok",
                "latency": elapsed,
                "http_status": response.status_code,
                "message": f"连接成功（HTTP {response.status_code}，耗时 {elapsed}ms）",
            }
        else:
            return {
                "status": "error",
                "latency": elapsed,
                "http_status": response.status_code,
                "message": f"服务端错误（HTTP {response.status_code}，耗时 {elapsed}ms）",
            }
    except httpx.TimeoutException:
        return {
            "status": "error",
            "latency": 5000,
            "message": "连接超时（5秒）",
        }
    except httpx.ConnectError as e:
        return {
            "status": "error",
            "latency": int((time.time() - start) * 1000),
            "message": f"连接失败: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "latency": int((time.time() - start) * 1000),
            "message": f"测试异常: {str(e)}",
        }
