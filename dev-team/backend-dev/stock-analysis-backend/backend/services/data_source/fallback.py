"""
数据源管理器和自动降级策略。

遵循架构方案第七节7.3容错与降级策略：
1. 连续3次失败自动切换备用源
2. 主数据源恢复后自动切回
3. 各模块有独立的数据源优先顺序，统一在 DataSourceManager 定义
4. 从 .env 读取 PRIMARY_DATA_SOURCE / FALLBACK_DATA_SOURCE / TDX_ENABLED
"""

import logging
from typing import List, Optional, Dict, Any

from backend.config.settings import settings
from backend.services.data_source.base import (
    BaseDataSource,
    QuoteData,
    KLineData,
    DataSourceStatus,
)

logger = logging.getLogger(__name__)


class DataSourceUnavailableError(Exception):
    """指定模块无可用的数据源"""
    def __init__(self, module_name: str, tried_sources: List[str]):
        self.module_name = module_name
        self.tried_sources = tried_sources
        super().__init__(
            f"模块 [{module_name}] 无可用数据源 (尝试: {', '.join(tried_sources)})"
        )


class DataSourceManager:
    """
    数据源管理器。

    核心变更：
    - 从 settings (env) 读取 primary/fallback 名称
    - 集中定义 模块→数据源优先顺序 映射
    - 支持 TDX_ENABLED 条件注册
    - get_active_for_module() 供各模块按优先顺序获取数据源
    - get_status_summary() 返回增加 modules / can_disable 字段
    """

    # 模块 → 数据源优先顺序映射（集中定义）
    MODULE_SOURCES: Dict[str, List[str]] = {
        # 市场行情
        "market_quotes":      ["eastmoney", "sina", "tdx_local"],       # 批量/单只行情快照
        "market_kline":       ["baostock"],        # K线数据（baostock最稳定）
        "market_sector":      ["akshare", "eastmoney"],              # 板块涨跌
        "market_limit":       ["akshare", "eastmoney"],                 # 涨跌停家数/涨停股池
        "market_northbound":  ["akshare"],                              # 北向资金（仅akshare）
        "market_overseas":    ["sina", "eastmoney"],                    # 外围市场/商品/汇率
        "market_news":        ["akshare", "eastmoney"],             # 财经新闻
        "market_premarket":   ["eastmoney", "sina"],                    # 盘前数据
        "market_tradeday":    ["akshare"],                              # 交易日历

        # 概念板块/个股资金流/基本面信息（通过 akshare 增强数据源）
        "market_concept":    ["akshare"],                               # 概念板块排行
        "market_fund_flow":  ["akshare"],                               # 个股资金流
        "market_stock_info": ["akshare"],                               # 个股基本面信息
        "market_sentiment":  ["akshare"],                               # 新闻舆情情绪（通过senti服务）

        # 智能选股
        "selection_pool":     ["tdx_local", "sina", "eastmoney"],          # 全市场股票池（新浪优先，东财push2被此网络屏蔽）
        "selection_finance":  ["akshare"],                              # 财务数据
        "selection_st":       ["akshare", "eastmoney"],                 # ST/停牌标记

        # 预警引擎
        "warning_quotes":     ["eastmoney", "sina", "tdx_local"],       # 预警行情
        "warning_finance":    ["akshare"],                              # 预警财务基础

        # 系统通用
        "stock_name_lookup":  ["eastmoney", "sina", "tdx_local"],       # 股票名称查询
    }

    def __init__(self):
        self._sources: Dict[str, BaseDataSource] = {}
        # 从 settings (env) 读取
        self._primary_name: str = settings.primary_data_source
        self._fallback_name: str = settings.fallback_data_source
        self._active_name: str = self._primary_name
        self._tdx_enabled: bool = settings.tdx_enabled

        # 缓存模块 → 数据源 反向映射（用于 get_status_summary）
        self._source_to_modules: Dict[str, List[str]] = {}
        self._rebuild_module_map()

    def _rebuild_module_map(self):
        """重建数据源→模块的反向映射"""
        self._source_to_modules = {}
        for module_name, source_list in self.MODULE_SOURCES.items():
            for source_name in source_list:
                self._source_to_modules.setdefault(source_name, []).append(module_name)

    def register(self, source: BaseDataSource):
        """注册数据源"""
        self._sources[source.name] = source

    # ─── 属性 ──────────────────────────────────

    @property
    def active(self) -> Optional[BaseDataSource]:
        return self._sources.get(self._active_name)

    @property
    def primary(self) -> Optional[BaseDataSource]:
        return self._sources.get(self._primary_name)

    @property
    def fallback(self) -> Optional[BaseDataSource]:
        return self._sources.get(self._fallback_name)

    # ─── 模块数据源查询 ────────────────────────

    def get_module_sources(self, module_name: str) -> List[str]:
        """获取指定模块的数据源优先顺序列表（名称）"""
        return self.MODULE_SOURCES.get(
            module_name,
            [self._primary_name, self._fallback_name]
        )

    def get_active_for_module(self, module_name: str) -> BaseDataSource:
        """
        获取指定模块当前可用的最优数据源。
        按模块优先顺序遍历，返回第一个可用的。
        全部不可用时抛 DataSourceUnavailableError。
        """
        for source_name in self.get_module_sources(module_name):
            source = self._sources.get(source_name)
            if source and source.is_available():
                return source
        raise DataSourceUnavailableError(
            module_name,
            self.get_module_sources(module_name)
        )

    # ─── 状态 ──────────────────────────────────

    def get_status_summary(self) -> List[Dict[str, Any]]:
        """获取所有数据源状态摘要（含模块使用关系）"""
        result = []
        for name, source in self._sources.items():
            is_primary = name == self._primary_name
            is_fallback = name == self._fallback_name
            result.append({
                "name": name,
                "type": source.__class__.__name__,
                "status": source.status,
                "is_active": name == self._active_name,
                "is_primary": is_primary,
                "is_fallback": is_fallback,
                "modules": self._source_to_modules.get(name, []),
                "can_disable": not is_primary and not is_fallback,
                "consecutive_failures": getattr(source, '_consecutive_failures', 0),
            })
        return result

    # ─── 交易时段判断 ──────────────────────────

    @staticmethod
    def _is_trading_time() -> bool:
        from datetime import datetime
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        h, m = now.hour, now.minute
        if (h == 9 and m >= 30) or (h == 10) or (h == 11 and m <= 30):
            return True
        if (h == 13) or (h == 14):
            return True
        if h == 15 and m == 0:
            return True
        return False

    # ─── 优先顺序（全局，用于 get_quote/get_quotes/get_kline）──

    def _priority_list(self) -> List[str]:
        """按优先级排序的全局数据源列表
        AKShare 不含在内：它只通过 get_active_for_module() 给专用模块。
        web_scrape 也不含在内：非交易日空返回时不应降级到慢速爬虫。
        主/备源从配置读取（.env 中的 PRIMARY_DATA_SOURCE / FALLBACK_DATA_SOURCE）。
        """
        network = [self._primary_name, self._fallback_name]
        local = ["tdx_local", "baostock"]
        emergency = []
        if self._is_trading_time():
            order = network + local + emergency
        else:
            order = local + network + emergency
        return [n for n in order if n in self._sources]

    def _next_available(self, skip_name: Optional[str] = None) -> Optional[BaseDataSource]:
        for name in self._priority_list():
            if skip_name and name == skip_name:
                continue
            source = self._sources.get(name)
            if source and source.is_available():
                return source
        return None

    async def auto_switch_if_needed(self):
        active = self.active
        if not active or not active.is_available():
            next_source = self._next_available()
            if next_source:
                self._active_name = next_source.name
            return
        if (
            self._active_name != self._primary_name
            and self.primary
            and self.primary.is_available()
        ):
            self._active_name = self._primary_name

    # ─── 通用多级降级查询 ──────────────────────

    async def _try_all_sources(self, method: str, *args, **kwargs):
        await self.auto_switch_if_needed()
        for name in self._priority_list():
            source = self._sources.get(name)
            if not source:
                continue
            if not source.is_available():
                continue
            try:
                handler = getattr(source, method, None)
                if handler is None:
                    continue
                result = await handler(*args, **kwargs)
                is_good = result is not None and (not isinstance(result, list) or len(result) > 0)
                if is_good:
                    if self._active_name != name:
                        self._active_name = name
                    return result
                # 空返回：继续降级尝试下一个源
                continue
            except Exception:
                source.record_failure()
                continue
        return None if method.startswith("get_quote") else []

    async def get_quote(self, code: str) -> Optional[QuoteData]:
        return await self._try_all_sources("get_quote", code)

    def reset_source_status(self, name: str = None):
        """重置数据源状态（失败计数和状态），name=None 时重置全部"""
        for n, src in self._sources.items():
            if name and n != name:
                continue
            src._consecutive_failures = 0
            src._status = DataSourceStatus.ONLINE
            src._last_failure_time = None
        if name:
            logger.info(f"数据源 [{name}] 状态已重置")
        else:
            logger.info("所有数据源状态已重置")

    async def get_quotes(self, codes: List[str]) -> List[QuoteData]:
        return await self._try_all_sources("get_quotes", codes)

    async def get_kline(self, code: str, count: int = 120) -> List[KLineData]:
        """
        获取K线数据。使用模块专用路由：只走 market_kline 的源顺序。
        不通过 _try_all_sources 通用优先级（避免了新浪/东财K线API不稳定拖垮数据源状态的问题）。
        """
        module_sources = self.get_module_sources("market_kline")
        for name in module_sources:
            source = self._sources.get(name)
            if not source:
                continue
            try:
                result = await source.get_kline(code, count)
                if result and len(result) > 0:
                    if self._active_name != name:
                        self._active_name = name
                    return result
            except Exception:
                continue
        return []

    # ─── 默认数据源注册 ────────────────────────

    def register_default_sources(self):
        """
        注册默认数据源。
        - TDX 仅当 tdx_enabled=True 时注册（Docker 环境禁用）
        - primary/fallback 从 settings 读取
        """
        from backend.services.data_source.eastmoney import EastMoneyDataSource
        from backend.services.data_source.sina import SinaDataSource
        from backend.services.data_source.baostock_data import BaostockDataSource
        from backend.services.data_source.web_scrape import WebScrapeDataSource

        self.register(EastMoneyDataSource())
        self.register(SinaDataSource())
        self.register(BaostockDataSource())
        self.register(WebScrapeDataSource())

        # 注册 AkShare 数据源（免费备用，概念板块/个股资金流/基本面信息等）
        try:
            from backend.services.data_source.akshare_data import AkShareDataSource
            self.register(AkShareDataSource())
            logger.info("AkShare 数据源已注册")
        except Exception as e:
            logger.warning(f"AkShare 数据源注册失败: {e}")

        if self._tdx_enabled:
            try:
                from backend.services.data_source.tdx_local import TDXLocalDataSource
                self.register(TDXLocalDataSource())
                logger.info("通达信本地数据源已注册")
            except Exception as e:
                logger.warning(f"通达信本地数据源注册失败: {e}")

            # 注册 tdx_api（HTTP 版 TDX 数据源）
            from backend.services.data_source.tdx_api import TdxApiDataSource
            self.register(TdxApiDataSource())
            logger.info(f"TDX API 数据源已注册: {settings.tdx_api_url}")

        # 从 settings 读取主/备配置（覆盖硬编码）
        self._primary_name = settings.primary_data_source
        self._fallback_name = settings.fallback_data_source
        self._active_name = self._primary_name

        # 更新模块映射中的名称（如有自定义源）
        self._rebuild_module_map()

        logger.info(
            f"数据源注册完成: 主={self._primary_name}, "
            f"备={self._fallback_name}, "
            f"TDX={'启用' if self._tdx_enabled else '禁用'}, "
            f"共 {len(self._sources)} 个"
        )
