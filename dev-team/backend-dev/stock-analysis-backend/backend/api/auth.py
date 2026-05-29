"""
用户认证与个人设置 API。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.user import User, LoginLog, UserPreference
from backend.services.auth_service import (
    authenticate_user, change_password, get_user_profile, update_profile,
    decode_token, create_access_token, create_refresh_token,
    init_default_users,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"], prefix="/user")


# ─── 依赖：获取当前用户 ───

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """从请求头解析Token并返回当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = auth[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    user_id = int(payload.get("sub", 0))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != 1:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return {"id": user.id, "username": user.username, "role": user.role, "need_change_password": user.need_change_password}


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """要求管理员权限"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ─── 登录 ───

@router.post("/login")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """账号密码登录"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    ip = request.client.host if request.client else ""

    result = await authenticate_user(db, username, password, ip)
    if not result["success"]:
        raise HTTPException(status_code=result.get("code", 401), detail=result["message"])
    return result


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """退出登录（前端清除Token即可）"""
    return {"success": True, "message": "已退出登录"}


@router.post("/refresh")
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """刷新Token"""
    body = await request.json()
    refresh = body.get("refresh_token", "")
    payload = decode_token(refresh)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh Token无效")
    user_id = int(payload.get("sub", 0))
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.status != 1:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {
        "token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
    }


# ─── 个人设置 ───

@router.get("/profile")
async def profile(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取个人信息"""
    p = await get_user_profile(db, current_user["id"])
    if not p:
        raise HTTPException(404, "用户不存在")
    return p


@router.put("/profile")
async def update_profile_api(request: Request, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """更新个人信息"""
    body = await request.json()
    result = await update_profile(db, current_user["id"], body)
    if not result["success"]:
        raise HTTPException(400, result["message"])
    return result


@router.put("/password")
async def change_password_api(request: Request, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """修改密码"""
    body = await request.json()
    result = await change_password(db, current_user["id"], body.get("old_password", ""), body.get("new_password", ""))
    if not result["success"]:
        raise HTTPException(400, result["message"])
    return result


@router.get("/logs")
async def login_logs(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取最近10条登录日志"""
    stmt = select(LoginLog).where(LoginLog.user_id == current_user["id"]).order_by(desc(LoginLog.login_at)).limit(10)
    result = await db.execute(stmt)
    logs = [{
        "login_at": l.login_at.isoformat() if l.login_at else "",
        "ip": l.ip,
        "device": l.device or "未知",
        "location": l.location or "-",
        "success": l.success == 1,
        "fail_reason": l.fail_reason or "",
    } for l in result.scalars().all()]
    return {"items": logs, "count": len(logs)}


# ─── 用户偏好 ───

@router.get("/preference")
async def get_preference(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取用户偏好"""
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == current_user["id"]))
    pref = result.scalar_one_or_none()
    if not pref:
        pref = UserPreference(user_id=current_user["id"])
        db.add(pref)
        await db.commit()
    return {
        "theme": pref.theme,
        "font_size": pref.font_size,
        "layout_mode": pref.layout_mode,
        "refresh_interval": pref.refresh_interval,
        "auto_refresh": pref.auto_refresh,
        "alert_refresh_interval": pref.alert_refresh_interval,
        "warn_sound": pref.warn_sound,
        "default_export_format": pref.default_export_format,
        "stock_sort": pref.stock_sort,
        "watchlist_sort": pref.watchlist_sort,
        "monitor_sort": pref.monitor_sort,
    }


@router.put("/preference")
async def update_preference(request: Request, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """更新用户偏好"""
    body = await request.json()
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == current_user["id"]))
    pref = result.scalar_one_or_none()
    if not pref:
        pref = UserPreference(user_id=current_user["id"])
        db.add(pref)
    allowed = ["theme", "font_size", "layout_mode", "refresh_interval", "auto_refresh",
               "alert_refresh_interval", "warn_sound", "default_export_format",
               "stock_sort", "watchlist_sort", "monitor_sort"]
    for key in allowed:
        if key in body:
            setattr(pref, key, body[key])
    await db.commit()
    return {"success": True}
