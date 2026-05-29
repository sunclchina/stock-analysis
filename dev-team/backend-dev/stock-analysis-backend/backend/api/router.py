"""
API路由注册中心。
所有API模块在此统一注册，统一前缀 /api/v1。
"""

from fastapi import APIRouter

from backend.api.config_api import router as config_router
from backend.api.custom_datasource import router as custom_datasource_router
from backend.api.market import router as market_router
from backend.api.dashboard import router as dashboard_router
from backend.api.warning import router as warning_router
from backend.api.warning_monitor import router as warning_monitor_router
from backend.api.selection import router as selection_router
from backend.api.analysis import router as analysis_router
from backend.api.portfolio import router as portfolio_router
from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router
from backend.api.help import router as help_router
from backend.api.help import admin_router as help_admin_router
from backend.api.note import router as note_router

# 全局API路由器，所有路径自动加 /api/v1 前缀
api_router = APIRouter(prefix="/api/v1")

# 注册各模块路由
api_router.include_router(config_router)               # M06 系统配置
api_router.include_router(custom_datasource_router)  # M06 自定义数据源
api_router.include_router(market_router)             # M02 实时行情
api_router.include_router(dashboard_router)  # M01 仪表盘
api_router.include_router(warning_router)         # M03 智能预警（列表/详情）
api_router.include_router(warning_monitor_router)  # M03 智能预警（监控面板/实时）
api_router.include_router(selection_router)  # M04 智能选股
api_router.include_router(analysis_router)   # M05 智能分析
api_router.include_router(portfolio_router)   # M07 资产组合管理
api_router.include_router(auth_router)        # 用户认证
api_router.include_router(admin_router)       # 管理员后台
api_router.include_router(help_router)         # 帮助中心（公开+需登录）
api_router.include_router(help_admin_router)   # 帮助中心（管理员）
api_router.include_router(note_router)            # 操盘笔记


@api_router.get("/health")
async def health_check():
    """
    健康检查端点。
    返回系统运行状态。
    """
    return {
        "status": "ok",
        "service": "stock-analysis-system",
        "version": "1.0.0",
    }
