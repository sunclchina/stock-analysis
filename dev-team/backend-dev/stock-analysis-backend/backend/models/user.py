"""
用户与权限模型。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float
from backend.config.database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(256), nullable=False)  # bcrypt hash
    nickname = Column(String(64), default="")
    avatar = Column(Text, default="")  # base64 or URL
    email = Column(String(128), default="")
    phone = Column(String(32), default="")
    role = Column(String(16), default="user")  # admin / user
    status = Column(Integer, default=1)  # 1=启用 0=禁用
    need_change_password = Column(Boolean, default=False)
    is_first_login = Column(Boolean, default=True)
    last_login_ip = Column(String(64), default="")
    last_login_at = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LoginLog(Base):
    """登录日志"""
    __tablename__ = "login_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    login_at = Column(DateTime, default=datetime.now)
    ip = Column(String(64), default="")
    device = Column(String(128), default="")
    location = Column(String(64), default="")
    success = Column(Integer, default=1)  # 1=成功 0=失败
    fail_reason = Column(String(128), default="")


class UserSession(Base):
    """用户会话"""
    __tablename__ = "user_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(512), nullable=False, index=True)
    refresh_token = Column(String(512), nullable=True)
    device = Column(String(128), default="")
    ip = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)


class UserPreference(Base):
    """用户偏好（合并原用户偏好）"""
    __tablename__ = "user_preference"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    theme = Column(String(16), default="light")  # light / dark / auto
    font_size = Column(String(8), default="14")  # 12 / 14 / 16
    layout_mode = Column(String(8), default="normal")  # normal / compact
    refresh_interval = Column(Integer, default=5)  # seconds
    auto_refresh = Column(Boolean, default=True)
    alert_refresh_interval = Column(Integer, default=1)
    warn_sound = Column(Boolean, default=True)
    default_export_format = Column(String(8), default="txt")  # txt / md / pdf
    stock_sort = Column(String(16), default="change_pct")
    watchlist_sort = Column(String(16), default="add_time")
    monitor_sort = Column(String(16), default="add_time")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
