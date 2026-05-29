"""
管理员 API：用户管理。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.user import User, UserSession
from backend.api.auth import get_current_user, require_admin
from backend.services.auth_service import _bcrypt_hash

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"], prefix="/admin/users", dependencies=[Depends(require_admin)])


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """获取用户列表"""
    result = await db.execute(select(User).order_by(desc(User.created_at)))
    users = [{
        "id": u.id,
        "username": u.username,
        "nickname": u.nickname,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "status": u.status,
        "last_login_ip": u.last_login_ip or "",
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else "",
        "created_at": u.created_at.isoformat() if u.created_at else "",
    } for u in result.scalars().all()]
    return {"items": users, "count": len(users)}


@router.post("")
async def create_user(request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """新增用户"""
    body = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "123456")
    nickname = body.get("nickname", username)
    role = body.get("role", "user")

    if not username or len(username) < 2:
        raise HTTPException(400, "账号至少2个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少6个字符")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "账号已存在")

    user = User(
        username=username,
        password=_bcrypt_hash(password),
        nickname=nickname,
        role=role,
        need_change_password=False,
        status=1,
    )
    db.add(user)
    await db.commit()
    return {"success": True, "message": f"用户 {username} 创建成功", "id": user.id}


@router.put("/{user_id}/status")
async def toggle_user_status(user_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """启用/禁用用户"""
    body = await request.json()
    new_status = body.get("status", 1)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == "admin":
        admin_count = (await db.execute(select(User).where(User.role == "admin", User.status == 1))).scalars().all()
        if len(admin_count) <= 1 and new_status == 0:
            raise HTTPException(400, "至少保留一个管理员账号")
    user.status = new_status
    await db.commit()
    return {"success": True}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """更新用户信息：用户名、昵称、角色"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    # 更新用户名
    if "username" in body:
        new_username = body["username"].strip()
        if len(new_username) < 2:
            raise HTTPException(400, "账号至少2个字符")
        # 查重
        dup = await db.execute(
            select(User).where(User.username == new_username, User.id != user_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(400, "账号已存在")
        user.username = new_username

    # 更新昵称
    if "nickname" in body:
        user.nickname = body["nickname"].strip()

    # 更新角色
    if "role" in body:
        new_role = body["role"]
        if new_role not in ("admin", "user"):
            raise HTTPException(400, "角色只能是 admin 或 user")
        # 防止将最后一个管理员降级
        if user.role == "admin" and new_role != "admin":
            admin_count = (
                await db.execute(
                    select(User).where(User.role == "admin", User.status == 1)
                )
            ).scalars().all()
            if len(admin_count) <= 1:
                raise HTTPException(400, "至少保留一个管理员账号")
        user.role = new_role

    # 更新密码（填空则不修改）
    if "password" in body:
        pwd = body["password"]
        if pwd:
            if len(pwd) < 6:
                raise HTTPException(400, "密码至少6个字符")
            user.password = _bcrypt_hash(pwd)

    await db.commit()
    return {"success": True, "message": "用户信息已更新"}


@router.put("/{user_id}/password")
async def reset_password(user_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """重置密码"""
    body = await request.json()
    new_pwd = body.get("new_password", "123456")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.password = _bcrypt_hash(new_pwd)
    await db.commit()
    return {"success": True, "message": "密码已重置"}


@router.post("/{user_id}/logout")
async def force_logout(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """强制下线"""
    result = await db.execute(select(UserSession).where(UserSession.user_id == user_id, UserSession.is_active == True))
    sessions = result.scalars().all()
    for s in sessions:
        s.is_active = False
    await db.commit()
    return {"success": True, "message": f"已强制 {len(sessions)} 个会话下线"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_admin)):
    """删除用户（保留系统管理员）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.role == "admin":
        admin_count = (await db.execute(select(User).where(User.role == "admin", User.status == 1))).scalars().all()
        if len(admin_count) <= 1:
            raise HTTPException(400, "至少保留一个管理员账号")
    await db.delete(user)
    await db.commit()
    return {"success": True, "message": "用户已删除"}
