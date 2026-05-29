"""
财务数据预加载器（FinancialDataLoader）。
每日开盘前加载财务数据到内存缓存，供选股引擎高效使用。

设计文档 §6.5.3：财务数据预加载 + 内存缓存
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, time as dtime

logger = logging.getLogger(__name__)


class FinancialDataLoader:
    """
    财务数据预加载器。
    
    特性：
    - 内存缓存所有A股的财务基本面数据
    - 每日首次访问触发加载（如果缓存过期）
    - 提供按股票代码查询的接口
    - 批量查询接口
    """

    def __init__(self, ttl_minutes: int = 60):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
        self._timestamp = 0.0
        self._ttl = ttl_minutes * 60  # 秒
        self._count = 0

    @property
    def is_loaded(self) -> bool:
        return self._loaded and (time.time() - self._timestamp) < self._ttl

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def get(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单只股票的财务数据"""
        return self._cache.get(code)

    def get_batch(self, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量获取财务数据"""
        return {c: self._cache[c] for c in codes if c in self._cache}

    def has(self, code: str) -> bool:
        return code in self._cache

    async def load(self, all_stocks: Optional[List[Dict[str, Any]]] = None) -> int:
        """
        加载财务数据到缓存。
        
        如果传入了 all_stocks，从现有stock dict中提取财务字段；
        否则尝试通过数据源接口加载。
        
        Returns:
            加载的股票数量
        """
        if self.is_loaded:
            return self._count

        loaded = 0
        if all_stocks:
            # 先用股票自身数据填充（TDX携带的基础字段）
            for s in all_stocks:
                code = s.get("code", "")
                if not code:
                    continue
                self._cache[code] = self._extract_finance_fields(s)
                loaded += 1
            # 再用akshare覆盖真实财务数据（若可用）
            try:
                asource = await self._load_from_source()
                if asource > 0:
                    loaded = asource
                    logger.info(f"财务缓存：akshare覆盖 {asource} 只")
            except Exception as e:
                logger.warning(f"财务数据源加载失败: {e}，使用股票自身数据")
        else:
            # 尝试通过数据源加载
            try:
                loaded = await self._load_from_source()
            except Exception as e:
                logger.warning(f"财务数据源加载失败: {e}")

        self._count = loaded
        self._timestamp = time.time()
        self._loaded = True
        logger.info(f"财务缓存就绪：{loaded} 只")
        return loaded

    async def _load_from_source(self) -> int:
        """从外部数据源加载财务数据（通过 akshare 东方财富接口）"""
        count = 0
        try:
            import akshare as ak

            # 尝试多个季度，取最新有数据的
            dates = ["20260331", "20251231", "20250930", "20250630", "20250331", "20241231"]
            df = None
            for d in dates:
                try:
                    logger.info(f"尝试加载 {d} 季度财务数据...")
                    df = await asyncio.to_thread(ak.stock_yjbb_em, d)
                    if df is not None and not df.empty:
                        logger.info(f"{d} 数据有效: {len(df)} 条")
                        break
                except Exception:
                    continue

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    try:
                        code = str(row.get("股票代码", "")).strip()
                        if not code:
                            continue
                        # 净利同比增长率
                        profit_growth = float(row.get("净利润-同比增长", 0) or 0)
                        # ROE 净资产收益率
                        roe = float(row.get("净资产收益率", 0) or 0)
                        # 毛利率（从营业收入换算）
                        gross_margin = float(row.get("毛利润", 0) or 0)

                        # 动态计算财务等级
                        if profit_growth > 20 and roe > 10:
                            finance_grade = "green"
                        elif profit_growth > 0 or roe > 5:
                            finance_grade = "yellow"
                        else:
                            finance_grade = "red"

                        # 动态计算风险评分（0-100，越低越好）
                        # 综合多项财务指标，拉开区分度
                        risk_score = 30  # 基础分

                        # 利润增长率评分（权重35%）
                        if profit_growth < -50:
                            risk_score += 35
                        elif profit_growth < -30:
                            risk_score += 25
                        elif profit_growth < -10:
                            risk_score += 15
                        elif profit_growth < 0:
                            risk_score += 8
                        elif profit_growth > 100:
                            risk_score -= 8
                        elif profit_growth > 50:
                            risk_score -= 5
                        elif profit_growth > 20:
                            risk_score -= 2

                        # ROE 净资产收益率（权重25%）
                        if roe < 0:
                            risk_score += 25
                        elif roe < 3:
                            risk_score += 15
                        elif roe < 8:
                            risk_score += 8
                        elif roe < 15:
                            risk_score += 3
                        elif roe > 25:
                            risk_score -= 5
                        elif roe > 15:
                            risk_score -= 3

                        # 毛利率（权重15%)
                        if gross_margin < -10:
                            risk_score += 15
                        elif gross_margin < 0:
                            risk_score += 10
                        elif gross_margin < 10:
                            risk_score += 5

                        # 负债率（权重25%）
                        debt_ratio = float(row.get("资产负债率", 50) or 50)
                        if debt_ratio > 80:
                            risk_score += 25
                        elif debt_ratio > 65:
                            risk_score += 15
                        elif debt_ratio > 50:
                            risk_score += 5
                        elif debt_ratio < 20:
                            risk_score -= 3

                        self._cache[code] = {
                            "finance_grade": finance_grade,
                            "finance_color": finance_grade,
                            "finance_abnormal_count": 0,
                            "deducted_profit": float(row.get("净利润-净利润", 0) or 0),
                            "profit_growth": profit_growth,
                            "net_profit_growth": profit_growth,
                            "roe": roe,
                            "risk_score": risk_score,
                            "industry": str(row.get("所处行业", "") or ""),
                            "operate_cashflow": float(row.get("净利润-净利润", 0) or 0) * 0.5,
                            "debt_ratio": debt_ratio,
                            "finance_data_available": True,
                            "gross_margin": gross_margin,
                        }
                        count += 1
                    except Exception:
                        continue
                logger.info(f"财务数据源加载完成：{count} 只有效数据")
        except ImportError:
            logger.warning("akshare 未安装，无法加载财务数据")
        except Exception as e:
            logger.warning(f"财务数据加载异常: {e}")
        return count

    @staticmethod
    def _extract_finance_fields(stock: Dict[str, Any]) -> Dict[str, Any]:
        """从股票字典中提取财务相关字段"""
        return {
            "finance_grade": stock.get("finance_grade", "yellow"),
            "finance_color": stock.get("finance_color", "yellow"),
            "finance_abnormal_count": stock.get("finance_abnormal_count", 0),
            "deducted_profit": stock.get("deducted_profit", 0),
            "profit_growth": stock.get("profit_growth", 0),
            "net_profit_growth": stock.get("net_profit_growth", 0),
            "roe": stock.get("roe", 0),
            "industry": stock.get("industry", ""),
            "operate_cashflow": stock.get("operate_cashflow", 0),
            "debt_ratio": stock.get("debt_ratio", 60.0),
            "finance_data_available": stock.get("finance_data_available", False),
            "gross_margin": stock.get("gross_margin", 0),
            "pe": stock.get("pe", 0),
            "pb": stock.get("pb", 0),
        }

    def enrich_stock(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """用缓存中的财务数据富集股票字典"""
        code = stock.get("code", "")
        cached = self._cache.get(code)
        if not cached:
            return stock

        has_data = cached.get("finance_data_available", False)

        for key, val in cached.items():
            if key == "finance_data_available":
                if val:
                    stock["finance_data_available"] = True
            elif key in ("finance_grade", "finance_color", "deducted_profit",
                         "profit_growth", "net_profit_growth", "roe",
                         "operate_cashflow", "debt_ratio", "industry",
                         "risk_score"):
                if has_data:
                    stock[key] = val
                    stock["finance_data_available"] = True
            else:
                existing = stock.get(key)
                if existing is None or existing == 0:
                    stock[key] = val

        return stock

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._loaded = False
        self._timestamp = 0
        self._count = 0
        logger.info("财务缓存已清空")


# 全局单例
financial_data_loader = FinancialDataLoader()
