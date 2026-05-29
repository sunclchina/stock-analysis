"""
M03 预警计算主引擎。

遵循架构方案5.2节盘中实时数据流：
- 多线程并行计算（10线程×每线程10只股票）
- 接收实时行情输入，输出预警事件
- 通过 WebSocket 推送 warning:trigger 事件

使用 asyncio 并发而非多线程（Python异步IO友好，避免GIL问题）。
行情获取和预警检查在同一个事件循环中并发执行。
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from backend.services.data_source.fallback import DataSourceManager
from backend.services.websocket_manager import ws_manager
from backend.services.warning_engine.price import (
    check_warnings_for_stock,
    WarningResult,
    DEFAULT_PRICE_WARNING_THRESHOLD,
    DEFAULT_UPDOWN_WARNING_THRESHOLD,
)
from backend.services.warning_engine.trend import check_trend_warning
from backend.services.warning_engine.resonance import check_resonance_warning
from backend.services.warning_engine.finance import check_finance_warning
from backend.services.warning_engine.event import check_event_warning
from backend.services.warning_engine.risk import check_risk_score
from backend.services.warning_engine.decision import check_decision_matrix, compute_decision

logger = logging.getLogger(__name__)


class WarningEngine:
    """
    预警主引擎。
    
    职责：
    1. 从监控池获取需要监控的股票列表
    2. 通过数据源获取实时行情
    3. 对每只股票并行运行预警检查
    4. 将触发的预警通过 WebSocket 推送
    5. 持久化预警记录到数据库
    """

    def __init__(
        self,
        data_source_manager: DataSourceManager,
        concurrency: int = 10,
    ):
        self._dsm = data_source_manager
        self._concurrency = concurrency
        self._running = False
        self._monitor_codes: List[str] = []
        self._previous_colors: Dict[str, str] = {}  # code → last color
        self._on_warning_callback: Optional[Callable] = None
        self._check_interval = 5.0  # 默认5秒

    @property
    def is_running(self) -> bool:
        return self._running

    def set_monitor_codes(self, codes: List[str]):
        """设置监控股票列表"""
        self._monitor_codes = codes

    def set_check_interval(self, seconds: float):
        """设置检查间隔"""
        self._check_interval = max(1.0, seconds)

    def set_on_warning_callback(self, callback: Callable):
        """设置预警回调函数（用于持久化到数据库）"""
        self._on_warning_callback = callback

    async def run_once(self) -> List[Dict[str, Any]]:
        """
        执行一次全量预警检查。
        
        返回本次触发的预警事件列表。
        """
        if not self._monitor_codes:
            logger.debug("预警引擎：监控列表为空，跳过检查")
            return []

        # 首次运行时刷新财务数据缓存
        if not getattr(self, '_finance_loaded', False):
            try:
                from backend.services.finance_enricher import fetch_finance_bulk
                fin_data = await asyncio.get_event_loop().run_in_executor(
                    None, fetch_finance_bulk, self._monitor_codes
                )
                for code, fin in fin_data.items():
                    if code in self._monitor_codes:
                        self.update_finance_cache(code, fin)
                self._finance_loaded = True
                logger.info(f"预警引擎: 财务数据缓存就绪 ({len(fin_data)} 只)")
            except Exception as e:
                logger.warning(f"预警引擎: 财务数据加载失败 {e}")

        triggered_events = []

        try:
            # 1. 批量获取实时行情
            quotes = await self._dsm.get_quotes(self._monitor_codes)
            if not quotes:
                logger.warning("预警引擎：获取行情数据为空")
                return []

            # 2. 并发运行预警检查
            tasks = []
            for q in quotes:
                task = self._check_stock_warnings(q)
                tasks.append(task)

            # 使用 asyncio.gather 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 3. 收集结果
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"预警检查异常: {result}")
                    continue
                if isinstance(result, list):
                    for warning in result:
                        if isinstance(warning, WarningResult) and warning.triggered:
                            event = self._build_warning_event(warning)
                            triggered_events.append(event)

            # 4. 推送预警事件到 WebSocket
            for event in triggered_events:
                try:
                    await ws_manager.broadcast_warning_trigger(event)
                except Exception as e:
                    logger.error(f"推送预警事件失败: {e}")

            # 5. 回调（持久化到数据库）
            if self._on_warning_callback and triggered_events:
                try:
                    await self._on_warning_callback(triggered_events)
                except Exception as e:
                    logger.error(f"预警持久化回调失败: {e}")

        except Exception as e:
            logger.error(f"预警引擎执行异常: {e}")

        return triggered_events

    async def _check_stock_warnings(self, quote) -> List[WarningResult]:
        """对单只股票运行全量预警检查（7大模块 + 综合决策矩阵）"""
        try:
            # 获取quote字段（处理QuoteData和字典两种格式）
            if hasattr(quote, 'name'):
                name = quote.name
                code = quote.code
                price = quote.price
                open_price = quote.open_price
                high_price = quote.high_price
                low_price = quote.low_price
                pre_close = quote.pre_close
                change_pct = quote.change_pct
                volume = quote.volume
            elif isinstance(quote, dict):
                name = quote.get('name', '')
                code = quote.get('code', '')
                price = quote.get('price', 0)
                open_price = quote.get('open', quote.get('open_price', 0))
                high_price = quote.get('high', quote.get('high_price', 0))
                low_price = quote.get('low', quote.get('low_price', 0))
                pre_close = quote.get('pre_close', 0)
                change_pct = quote.get('change_pct', 0)
                volume = quote.get('volume', 0)
            else:
                return []

            if price <= 0:
                return []

            # ── 获取K线数据用于指标计算 ──
            closes = self._get_cached_closes(code)
            highs = self._get_cached_highs(code)
            lows = self._get_cached_lows(code)
            volumes = self._get_cached_volumes(code, volume)

            # ── 1. 基础预警（价格+涨跌） ──
            base_results = check_warnings_for_stock(
                code=code,
                name=name,
                price=price,
                open_price=open_price,
                pre_close=pre_close,
            )

            results = list(base_results)

            # ── 2. 趋势预警 ──
            trend_result = check_trend_warning(
                code=code, name=name, price=price, closes=closes,
            )
            if trend_result:
                results.append(trend_result)

            # ── 3. 共振预警 ──
            resonance_result = check_resonance_warning(
                code=code, name=name, price=price, change_pct=change_pct,
                opens=closes, highs=highs, lows=lows, closes=closes, volumes=volumes,
            )
            if resonance_result:
                results.append(resonance_result)

            # ── 4. 财务预警（使用缓存数据或默认值） ──
            finance_result = check_finance_warning(
                code=code, name=name, price=price,
                pe=self._get_cached_finance(code, 'pe'),
                pb=self._get_cached_finance(code, 'pb'),
                roe=self._get_cached_finance(code, 'roe'),
                revenue_growth=self._get_cached_finance(code, 'revenue_growth'),
                profit_growth=self._get_cached_finance(code, 'profit_growth'),
                debt_ratio=self._get_cached_finance(code, 'debt_ratio'),
            )
            if finance_result:
                results.append(finance_result)

            # ── 5. 突发预警 ──
            event_result = check_event_warning(
                code=code, name=name,
                price=price, pre_close=pre_close,
                open_price=open_price, high_price=high_price, low_price=low_price,
                volumes=volumes, closes=closes,
                turnover_rate=self._get_cached_finance(code, 'turnover_rate'),
            )
            if event_result:
                results.append(event_result)

            # ── 6. 风险评分 ──
            finance_color = finance_result.indicator_color if finance_result else "gray"
            event_color = event_result.indicator_color if event_result else "gray"

            risk_result = check_risk_score(
                code=code, name=name,
                closes=closes, price=price, pre_close=pre_close,
                volumes=volumes,
                is_trading_hours=False,
                finance_color=finance_color,
                event_color=event_color,
            )
            if risk_result:
                results.append(risk_result)

            # ── 7. 综合决策矩阵 ──
            all_warnings = {}
            for r in results:
                if r.warning_type not in ("risk", "decision"):
                    all_warnings[r.warning_type] = r
            all_warnings["risk"] = risk_result

            decision_result = check_decision_matrix(
                code=code, name=name,
                stock_warnings=all_warnings,
            )
            if decision_result:
                results.append(decision_result)

            # 过滤：仅当颜色变化时才推送
            filtered = []
            for r in results:
                prev_color = self._previous_colors.get(f"{code}:{r.warning_type}", "gray")
                if r.indicator_color != prev_color:
                    self._previous_colors[f"{code}:{r.warning_type}"] = r.indicator_color
                    filtered.append(r)

            return filtered

        except Exception as e:
            logger.warning(f"预警检查异常 [{getattr(quote, 'code', 'unknown')}]: {e}")
            return []

    # ── 缓存辅助方法 ──
    _kline_cache: Dict[str, List[float]] = {}
    _finance_cache: Dict[str, Dict[str, float]] = {}

    def _get_cached_closes(self, code: str) -> List[float]:
        """获取缓存的收盘价序列"""
        return self._kline_cache.get(f"{code}:closes", [])

    def _get_cached_highs(self, code: str) -> List[float]:
        """获取缓存的最高价序列"""
        return self._kline_cache.get(f"{code}:highs", [])

    def _get_cached_lows(self, code: str) -> List[float]:
        """获取缓存的最低价序列"""
        return self._kline_cache.get(f"{code}:lows", [])

    def _get_cached_volumes(self, code: str, current_volume: float) -> List[float]:
        """获取缓存的成交量序列（追加当前值）"""
        volumes = list(self._kline_cache.get(f"{code}:volumes", []))
        if current_volume > 0:
            volumes.append(current_volume)
        return volumes

    def _get_cached_finance(self, code: str, key: str) -> Optional[float]:
        """获取缓存的财务数据"""
        fin = self._finance_cache.get(code, {})
        return fin.get(key)

    def update_kline_cache(self, code: str, closes: List[float],
                           highs: Optional[List[float]] = None,
                           lows: Optional[List[float]] = None,
                           volumes: Optional[List[float]] = None):
        """更新K线缓存（供外部调用）"""
        self._kline_cache[f"{code}:closes"] = closes
        if highs:
            self._kline_cache[f"{code}:highs"] = highs
        if lows:
            self._kline_cache[f"{code}:lows"] = lows
        if volumes:
            self._kline_cache[f"{code}:volumes"] = volumes

    def update_finance_cache(self, code: str, finance_data: Dict[str, Optional[float]]):
        """更新财务数据缓存（供外部调用，如定时任务）"""
        self._finance_cache[code] = finance_data

    @staticmethod
    def _extract_score_from_result(result: Optional[WarningResult]) -> Optional[float]:
        """从预警结果中提取数值评分"""
        if result is None:
            return None
        import json
        try:
            if isinstance(result.detail, str):
                detail = json.loads(result.detail)
            else:
                detail = result.detail

            type_score_keys = {
                "trend": "trend_score",
                "resonance": "resonance_score",
                "finance": "finance_score",
                "event": "event_score",
                "risk": "risk_score",
            }
            key = type_score_keys.get(result.warning_type)
            if key:
                val = detail.get(key)
                if val is not None:
                    return float(val)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass
        return None

    def _build_warning_event(self, warning: WarningResult) -> Dict[str, Any]:
        """构建预警事件数据结构"""
        return {
            "code": warning.code,
            "warning_type": warning.warning_type,
            "warning_level": warning.warning_level,
            "title": warning.title,
            "detail": warning.detail,
            "indicator_color": warning.indicator_color,
            "triggered": warning.triggered,
            "triggered_at": datetime.now().isoformat(),
        }

    async def run_loop(self):
        """持续运行预警检查循环"""
        self._running = True
        logger.info(f"预警引擎已启动 (间隔: {self._check_interval}s, 并发: {self._concurrency})")

        while self._running:
            try:
                events = await self.run_once()
                if events:
                    logger.info(f"预警引擎：触发 {len(events)} 个预警事件")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"预警引擎循环异常: {e}")

            await asyncio.sleep(self._check_interval)

        logger.info("预警引擎已停止")

    async def resolve_warning(self, code: str, warning_type: str):
        """解除预警，重置颜色状态"""
        key = f"{code}:{warning_type}"
        if key in self._previous_colors:
            old_color = self._previous_colors.pop(key)
            logger.info(f"预警解除: {code}/{warning_type} (原颜色: {old_color})")
            try:
                await ws_manager.broadcast_warning_resolve(f"{code}:{warning_type}")
            except Exception as e:
                logger.error(f"推送预警解除事件失败: {e}")

    def stop(self):
        """停止预警引擎"""
        self._running = False
        logger.info("预警引擎停止信号已发送")


# 用于单次检查的快捷函数
async def check_all_warnings(
    dsm: DataSourceManager,
    monitor_codes: List[str],
) -> List[Dict[str, Any]]:
    """
    便捷函数：执行一次全量预警检查。
    
    Args:
        dsm: 数据源管理器
        monitor_codes: 监控股票列表
        
    Returns:
        触发的预警事件列表
    """
    engine = WarningEngine(dsm)
    engine.set_monitor_codes(monitor_codes)
    return await engine.run_once()
