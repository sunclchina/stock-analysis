"""
股票分析与投资决策系统 — FastAPI应用入口。

遵循架构方案：
- 统一前缀 /api/v1（通过 router.py 注册）
- CORS中间件允许前端8080访问
- 启动时初始化数据库和数据源
- 独立端口运行（默认8000，非8080）

阶段2更新：
- 集成预警引擎（M03）
- 启动时加载监控池列表
- 定时行情刷新与预警检查
"""

import json
import logging
import asyncio
import os
from contextlib import asynccontextmanager

# 全局禁用 tqdm 进度条（AKShare 内部大量使用，输出到 stdout 干扰 asyncio 事件循环）
os.environ["TQDM_DISABLE"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from backend.config.settings import settings
from backend.config.database import init_db, async_session_factory
from backend.api.router import api_router
from backend.services.websocket_manager import ws_manager
from backend.services.scheduler import scheduler
from backend.services.data_source.fallback import DataSourceManager
from backend.services.warning_engine import WarningEngine
from backend.models.config import MonitorItem

# 数据源管理器全局单例
data_source_manager = DataSourceManager()

# 预警引擎全局单例
warning_engine = WarningEngine(data_source_manager)

# 日志配置
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _load_monitor_codes() -> list:
    """从数据库加载监控池股票列表"""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(MonitorItem).where(MonitorItem.is_active == True)
            )
            items = result.scalars().all()
            codes = [item.code for item in items]
            logger.info(f"从数据库加载监控池：{len(codes)} 只股票")
            return codes
    except Exception as e:
        logger.warning(f"加载监控池失败: {e}")
        return []


async def _warning_persistence_callback(events: list):
    """
    预警事件持久化回调。
    将触发的预警写入数据库 warning_records 表。
    """
    from backend.models.warning import WarningRecord

    try:
        async with async_session_factory() as session:
            for event in events:
                record = WarningRecord(
                    code=event.get("code", ""),
                    warning_type=event.get("warning_type", ""),
                    warning_level=event.get("warning_level", "info"),
                    title=event.get("title", ""),
                    detail=event.get("detail", ""),
                    indicator_color=event.get("indicator_color", "gray"),
                )
                session.add(record)
            await session.commit()
            logger.debug(f"已持久化 {len(events)} 条预警记录")
    except Exception as e:
        logger.error(f"预警记录持久化失败: {e}")


async def _is_trading_day() -> bool:
    """判断今天是否为A股交易日。直连新浪 API，非交易日返回 False。"""
    from backend.utils.sina_trade_calendar import is_trading_day
    return is_trading_day()


async def _market_refresh_task():
    """
    定时行情刷新任务。
    同时驱动预警引擎检查。
    非交易日自动跳过。
    """
    try:
        # 非交易日跳过
        if not await _is_trading_day():
            return

        # 获取最新监控池列表
        codes = await _load_monitor_codes()
        if codes:
            warning_engine.set_monitor_codes(codes)
            events = await warning_engine.run_once()
            if events:
                logger.info(f"定时行情刷新：触发 {len(events)} 个预警")

        # 广播行情心跳
        dsm = data_source_manager
        if codes:
            quotes = await dsm.get_quotes(codes)
            if quotes:
                await ws_manager.broadcast_market_update([
                    q.to_dict() if hasattr(q, 'to_dict') else q
                    for q in quotes
                ])
    except Exception as e:
        logger.error(f"定时行情刷新异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 60)
    logger.info("股票分析与投资决策系统 后端启动中...")
    logger.info(f"端口: {settings.backend_port}")
    logger.info(f"数据源: {settings.primary_data_source} (主) / {settings.fallback_data_source} (备)")
    logger.info("=" * 60)

    # 1. 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")

    # 1.5 初始化默认用户
    try:
        async with async_session_factory() as session:
            from backend.services.auth_service import init_default_users
            await init_default_users(session)
    except Exception as e:
        logger.warning(f"默认用户初始化失败: {e}")

    # 1.6 初始化帮助中心默认数据
    try:
        from backend.api.help import init_help_data
        await init_help_data()
        logger.info("帮助中心数据初始化完成")
    except Exception as e:
        logger.warning(f"帮助中心数据初始化失败: {e}")

    # 2. 注册默认数据源
    data_source_manager.register_default_sources()
    logger.info("数据源注册完成")

    # 重置AKShare数据源为在线状态（避免上次运行累计失败导致下线）
    from backend.services.data_source.base import DataSourceStatus
    try:
        akshare_source = data_source_manager._sources.get("akshare")
        if akshare_source and akshare_source.status == DataSourceStatus.OFFLINE:
            akshare_source._status = DataSourceStatus.ONLINE
            akshare_source._consecutive_failures = 0
            logger.info("AKShare数据源状态已重置为在线")
    except Exception as e:
        logger.warning(f"AKShare数据源重置失败: {e}")

    # 3. 加载监控池并配置预警引擎
    monitor_codes = await _load_monitor_codes()
    if monitor_codes:
        warning_engine.set_monitor_codes(monitor_codes)
        warning_engine.set_on_warning_callback(_warning_persistence_callback)
        logger.info(f"预警引擎就绪：监控 {len(monitor_codes)} 只股票")

    # 4. 启动定时任务调度器
    scheduler.start()
    # 注册行情刷新任务（默认5秒间隔）
    scheduler.add_interval_job("market_refresh", _market_refresh_task, seconds=30)
    logger.info("定时任务调度器已启动（行情刷新间隔：30秒，非交易日自动跳过）")

    # 5. 发送心跳任务（30秒间隔）
    async def _heartbeat_task():
        try:
            await ws_manager.send_heartbeat()
        except Exception as e:
            logger.debug(f"心跳发送异常: {e}")
    scheduler.add_interval_job("heartbeat", _heartbeat_task, seconds=30)
    logger.info("WebSocket心跳已启动（间隔：30秒）")

    # 6. 选股模块：非交易时段定时任务（文档§3.3.2）
    from backend.services.selection_engine.fixed import SELECTION_TEMPLATES

    async def _selection_preload_data():
        """08:30 全市场数据预加载：财务、事件、ST状态等低频数据（非交易日跳过）"""
        if not await _is_trading_day():
            logger.debug("非交易日，跳过选股预加载")
            return
        logger.info("选股预加载：开始加载低频数据...")
        try:
            from backend.api.selection import _load_all_stocks
            stocks = await _load_all_stocks()
            if stocks:
                logger.info(f"选股预加载完成：{len(stocks)} 只股票")
        except Exception as e:
            logger.error(f"选股预加载失败: {e}")

    async def _selection_pre_filter():
        """08:45 第1层过滤预计算（非交易日跳过）"""
        if not await _is_trading_day():
            logger.debug("非交易日，跳过选股预过滤")
            return
        logger.info("选股预过滤：开始第1层预计算...")
        try:
            from backend.api.selection import _load_all_stocks
            stocks = await _load_all_stocks()
            if stocks:
                from backend.services.selection_engine.fixed import _apply_layer1, SELECTION_TEMPLATES
                for tid, template in SELECTION_TEMPLATES.items():
                    l1 = _apply_layer1(stocks, template.layer1_filters)
                    logger.info(f"选股预过滤 [{tid}]: 第1层通过 {len(l1)} 只")
        except Exception as e:
            logger.error(f"选股预过滤失败: {e}")

    async def _selection_close_archive():
        """15:10 收盘定稿归档（非交易日跳过）"""
        if not await _is_trading_day():
            logger.debug("非交易日，跳过选股收盘归档")
            return
        logger.info("选股收盘归档：保存当日最终结果...")
        try:
            import json, os
            from datetime import date
            from backend.api.selection import _load_all_stocks
            from backend.services.selection_engine.fixed import fixed_selection
            archive_dir = settings.data_dir / "selection_snapshots"
            archive_dir.mkdir(parents=True, exist_ok=True)
            stocks = await _load_all_stocks()
            if stocks:
                for tid in SELECTION_TEMPLATES:
                    result = fixed_selection(tid, stocks)
                    fname = archive_dir / f"{tid}_{date.today().isoformat()}.json"
                    with open(fname, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, default=str)
                    logger.info(f"收盘归档 [{tid}]: {len(result['results'])} 只 -> {fname}")
        except Exception as e:
            logger.error(f"选股收盘归档失败: {e}")

    async def _selection_enrich_eastmoney():
        """08:35 东方财富换手率+行业数据在线富集（非交易日跳过）"""
        if not await _is_trading_day():
            logger.debug("非交易日，跳过东财富集")
            return
        logger.info("东财富集：开始在线抓取...")
        try:
            from backend.services.eastmoney_enricher import get_enricher
            enricher = get_enricher()
            count = await enricher.fetch_and_cache()
            logger.info(f"东财富集完成：{count} 只")
        except Exception as e:
            logger.error(f"东财富集失败: {e}")

    # 注册选股 cron 任务（任务内已加非交易日跳过判断）
    scheduler.add_cron_job("selection_peload", _selection_preload_data, hour=8, minute=30)
    scheduler.add_cron_job("selection_enrich", _selection_enrich_eastmoney, hour=8, minute=35)
    scheduler.add_cron_job("selection_prefilter", _selection_pre_filter, hour=8, minute=45)
    scheduler.add_cron_job("selection_archive", _selection_close_archive, hour=15, minute=10)
    logger.info("选股定时任务已注册：08:30预加载 / 08:35东财富集 / 08:45预过滤 / 15:10收盘归档")

    # 6.5 自动交易引擎定时扫描
    async def _auto_trade_task():
        """自动交易扫描任务（非交易日跳过）"""
        if not await _is_trading_day():
            return
        try:
            from backend.services.auto_trade_engine import run_auto_trade
            await run_auto_trade()
        except Exception as e:
            logger.warning(f"自动交易执行异常: {e}")

    scheduler.add_interval_job("auto_trade", _auto_trade_task, seconds=60)
    logger.info("自动交易引擎已启动：每60秒扫描一次")

    # 7. AkShare后台缓存预热（注释掉：预热期间tqdm进度条干扰asyncio事件循环，
    # 导致所有API请求卡住。数据改为按需加载，首次请求稍慢但不会阻塞。）
    # try:
    #     from backend.api.market import _warm_akshare
    #     asyncio.create_task(_warm_akshare())
    #     logger.info("AkShare缓存预热任务已创建")
    # except Exception as e:
    #     logger.warning(f"AkShare预热失败: {e}")

    # 后台预热选股数据（用户首次进入避免等待）
    async def _warm_selection():
        """后台预加载选股数据"""
        try:
            from backend.api.selection import load
            ss = await load()
            logger.info(f"选股数据预热完成: {len(ss)} 只")
        except Exception as e:
            logger.warning(f"选股数据预热失败: {e}")
    asyncio.create_task(_warm_selection())

    yield  # 应用运行中

    # 应用关闭
    logger.info("正在关闭系统...")
    warning_engine.stop()
    scheduler.stop()
    logger.info("系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="股票分析与投资决策系统 API",
    description="""
    个人股票分析与投资决策系统后端。
    
    模块：
    - M01 系统仪表盘
    - M02 实时行情
    - M03 智能预警
    - M04 智能选股
    - M05 智能分析
    - M06 系统配置
    
    数据源：
    - 主力：通达信本地（ds_stk.dat / .day）
    - 备用：新浪财经 / 东方财富
    
    预警引擎（7大模块 + 综合决策矩阵）：
    - 价格预警 / 涨跌预警 / 趋势预警 / 共振预警
    - 财务预警 / 突发预警 / 风险评分
    - 综合决策矩阵（操作建议）
    - WebSocket实时推送（warning:trigger / warning:resolve）
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS中间件：允许前端（8080端口）跨域访问
cors_origins = settings.cors_origins
if isinstance(cors_origins, str):
    cors_origins = json.loads(cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有API路由（统一前缀 /api/v1）
app.include_router(api_router)

# WebSocket端点
from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await ws_manager.connect(websocket)
    logger.info(f"WebSocket客户端已连接 (当前连接数: {ws_manager.count})")
    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            # 客户端消息处理
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")
                if msg_type == "ping":
                    import time
                    await websocket.send_text(json.dumps({"event": "pong", "data": {"timestamp": time.time()}}))
                elif msg_type == "warning:resolve":
                    # 客户端触发预警解除
                    code = msg.get("code", "")
                    warning_type = msg.get("warning_type", "")
                    if code and warning_type:
                        await warning_engine.resolve_warning(code, warning_type)
                        logger.info(f"WebSocket请求解除预警: {code}/{warning_type}")
                elif msg_type == "subscribe":
                    # 订阅特定股票（预留）
                    codes = msg.get("codes", [])
                    logger.info(f"WebSocket订阅股票: {codes}")
                elif msg_type == "unsubscribe":
                    # 取消订阅（预留）
                    codes = msg.get("codes", [])
                    logger.info(f"WebSocket取消订阅: {codes}")
            except (json.JSONDecodeError, Exception) as e:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket客户端已断开 (当前连接数: {ws_manager.count})")


# 静态文件服务（分析报告下载 + 前端静态文件）
try:
    import os
    os.makedirs("./data/reports", exist_ok=True)
    app.mount("/api/v1/download", StaticFiles(directory="./data/reports"), name="reports")
    logger.info("静态文件服务就绪：./data/reports")
except Exception as e:
    logger.warning(f"静态文件目录挂载失败（可忽略）: {e}")

# 前端静态文件服务（生产模式：单端口部署）
try:
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir) and os.path.exists(os.path.join(static_dir, "index.html")):
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        
        # 挂载静态资源（JS/CSS/图片等）
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="frontend_assets")
        
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            # API 请求直接透传
            if full_path.startswith("api/") or full_path.startswith("ws"):
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            # 其他请求返回 index.html（SPA 路由）
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))
        
        logger.info(f"前端静态文件服务就绪：{static_dir}")
    else:
        logger.info("前端静态文件未构建，跳过（开发模式正常）")
except Exception as e:
    logger.warning(f"前端静态文件挂载失败（可忽略）: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower(),
    )
