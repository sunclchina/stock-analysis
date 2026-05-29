"""
用户认证服务：登录、Token、密码管理。
"""

import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import jwt, JWTError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User, LoginLog, UserSession, UserPreference
from backend.config.settings import settings

# JWT配置
JWT_SECRET = settings.jwt_secret if hasattr(settings, 'jwt_secret') else secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
REFRESH_TOKEN_EXPIRE_DAYS = 7

LOGIN_MAX_ATTEMPTS = 10
LOGIN_LOCK_MINUTES = 5

# 缓存登录失败次数（内存，进程重启重置）
_login_attempt_cache: Dict[str, List[datetime]] = {}


def _bcrypt_hash(password: str) -> str:
    """使用 bcrypt 或 sha256 哈希密码"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _bcrypt_verify(password: str, hashed: str) -> bool:
    """验证密码"""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_access_token(user_id: int, role: str) -> str:
    """创建 JWT Access Token"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """创建 Refresh Token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """解码 JWT Token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def check_login_locked(ip: str) -> bool:
    """检查IP是否被锁定"""
    now = datetime.now()
    attempts = _login_attempt_cache.get(ip, [])
    attempts = [t for t in attempts if t > now - timedelta(minutes=LOGIN_LOCK_MINUTES)]
    _login_attempt_cache[ip] = attempts
    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def record_login_attempt(ip: str, success: bool):
    """记录登录尝试"""
    if success:
        _login_attempt_cache.pop(ip, None)
    else:
        if ip not in _login_attempt_cache:
            _login_attempt_cache[ip] = []
        _login_attempt_cache[ip].append(datetime.now())


async def authenticate_user(db: AsyncSession, username: str, password: str, ip: str) -> Dict:
    """用户登录认证"""
    # 检查IP锁定
    if check_login_locked(ip):
        return {"success": False, "message": "登录已锁定，请10分钟后再试", "code": 429}

    # 查询用户
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        record_login_attempt(ip, False)
        await _log_login(db, None, ip, False, "账号不存在")
        return {"success": False, "message": "账号或密码错误", "code": 401}

    if user.status != 1:
        record_login_attempt(ip, False)
        await _log_login(db, user.id, ip, False, "账号已禁用")
        return {"success": False, "message": "账号已被禁用", "code": 403}

    if not _bcrypt_verify(password, user.password):
        record_login_attempt(ip, False)
        await _log_login(db, user.id, ip, False, "密码错误")
        return {"success": False, "message": "账号或密码错误", "code": 401}

    # 登录成功
    record_login_attempt(ip, True)
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    # 更新用户
    user.last_login_ip = ip
    user.last_login_at = datetime.now()
    if user.is_first_login:
        user.is_first_login = False

    # 保存会话
    session = UserSession(
        user_id=user.id,
        token=access_token,
        refresh_token=refresh_token,
        ip=ip,
        expires_at=datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )
    db.add(session)

    # 登录日志
    await _log_login(db, user.id, ip, True, "")

    await db.commit()

    return {
        "success": True,
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname or user.username,
            "role": user.role,
            "avatar": user.avatar or "",
            "need_change_password": user.need_change_password,
        },
    }


async def _log_login(db: AsyncSession, user_id: Optional[int], ip: str, success: bool, reason: str = ""):
    """写入登录日志"""
    log = LoginLog(
        user_id=user_id or 0,
        ip=ip,
        device="",  # 前端可传入
        success=1 if success else 0,
        fail_reason=reason,
    )
    db.add(log)


async def change_password(db: AsyncSession, user_id: int, old_pwd: str, new_pwd: str) -> Dict:
    """修改密码"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "message": "用户不存在"}

    if not _bcrypt_verify(old_pwd, user.password):
        return {"success": False, "message": "原密码错误"}

    if len(new_pwd) < 6:
        return {"success": False, "message": "新密码长度不能少于6位"}

    user.password = _bcrypt_hash(new_pwd)
    user.need_change_password = False
    user.last_password_change = datetime.now()
    await db.commit()

    return {"success": True, "message": "密码修改成功，请重新登录"}


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[Dict]:
    """获取用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "need_change_password": user.need_change_password,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


async def update_profile(db: AsyncSession, user_id: int, data: Dict) -> Dict:
    """更新用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "message": "用户不存在"}

    for key in ["nickname", "avatar", "email", "phone"]:
        if key in data:
            setattr(user, key, data[key])

    await db.commit()
    return {"success": True, "message": "更新成功"}


async def init_default_users(db: AsyncSession):
    """首次启动时创建默认管理员账号"""
    result = await db.execute(select(User).limit(1))
    if result.first():
        return  # 已有用户，跳过

    # 创建管理员
    from backend.config.settings import settings as _s
    admin_user = User(
        username=_s.default_admin_username,
        password=_bcrypt_hash(_s.default_admin_password),
        nickname=_s.default_admin_nickname,
        role="admin",
        need_change_password=_s.force_change_password,
        is_first_login=True,
        status=1,
    )
    db.add(admin_user)
    await db.flush()

    # 创建管理员默认偏好
    pref = UserPreference(user_id=admin_user.id)
    db.add(pref)

    # 创建演示用户
    if _s.enable_demo_user:
        demo = User(
            username=_s.demo_username,
            password=_bcrypt_hash(_s.demo_password),
            nickname=_s.demo_nickname,
            role="user",
            need_change_password=_s.force_change_password,
            is_first_login=True,
            status=1,
        )
        db.add(demo)
        await db.flush()
        pref2 = UserPreference(user_id=demo.id)
        db.add(pref2)

    await db.commit()
    import logging
    logging.getLogger(__name__).info("默认管理员账号已创建")
