"""
数据库连接配置。
使用 SQLAlchemy 2.0 async，默认 SQLite（可平滑迁移至 PostgreSQL）。
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import settings


# 异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=(settings.log_level == "DEBUG"),
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# 会话工厂
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
