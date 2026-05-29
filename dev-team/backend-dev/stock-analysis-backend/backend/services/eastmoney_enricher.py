"""
东方财富数据增量富集器。
定时抓取换手率(f8)和行业(f103)，本地缓存，限速防反爬。

使用方式：
  enricher = EastMoneyEnricher()
  await enricher.enrich_stocks(tdx_stocks_list)
  
缓存文件：data/eastmoney_enrich_cache.json
定时策略：交易日 08:35 自动运行
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ─── 缓存文件路径 ─────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CACHE_FILE = os.path.join(CACHE_DIR, "eastmoney_enrich_cache.json")

# ─── 请求参数 ─────────────────────────────────────────
EASTMONEY_URL = "https://push2.eastmoney.com/api/qt/clist/get"
PAGE_SIZE = 100          # 每页100只
MIN_DELAY = 2.5          # 最小延迟秒
MAX_DELAY = 4.5          # 最大延迟秒
MAX_RETRIES = 3          # 每页重试次数
STALE_DAYS = 1           # 缓存过期天数（1天后需刷新）

# ─── User-Agent 池（随机化） ──────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

REFERERS = [
    "https://quote.eastmoney.com/",
    "https://data.eastmoney.com/",
    "https://finance.eastmoney.com/",
    "https://www.eastmoney.com/",
    "https://push2.eastmoney.com/",
]


class EastMoneyEnricher:
    """东方财富数据富集器"""

    def __init__(self):
        self._cache_dir = CACHE_DIR
        self._cache_file = CACHE_FILE
        os.makedirs(self._cache_dir, exist_ok=True)
        self._load_cache()

    # ═══════════════════════════════════════════════════
    # 缓存管理
    # ═══════════════════════════════════════════════════

    def _load_cache(self):
        """加载本地缓存"""
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[str] = None  # ISO格式时间戳
        if os.path.isfile(self._cache_file):
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = data.get("stocks", {})
                    self._cache_time = data.get("updated_at")
                logger.info(f"东财富集缓存已加载: {len(self._cache)}只, 更新于{self._cache_time}")
            except Exception as e:
                logger.warning(f"东财富集缓存加载失败: {e}")
                self._cache = {}
                self._cache_time = None

    def _save_cache(self):
        """保存缓存到本地文件"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "stocks": self._cache,
        }
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            self._cache_time = data["updated_at"]
            logger.info(f"东财富集缓存已保存: {len(self._cache)}只")
        except Exception as e:
            logger.warning(f"东财富集缓存保存失败: {e}")

    def is_cache_fresh(self) -> bool:
        """检查缓存是否仍有效（当天数据）"""
        if not self._cache_time:
            return False
        try:
            cached_date = datetime.fromisoformat(self._cache_time).date()
            return cached_date == date.today()
        except (ValueError, TypeError):
            return False

    def get_enriched(self, code: str) -> Dict[str, Any]:
        """获取单只股票的富集数据"""
        return self._cache.get(code, {})

    def apply_to_stock(self, stock: Dict[str, Any]) -> bool:
        """将缓存中的富集数据应用到股票dict，返回是否有更新"""
        code = stock.get("code", "")
        enriched = self._cache.get(code)
        if not enriched:
            return False
        updated = False
        tr = enriched.get("turnover_rate")
        if tr is not None and (not stock.get("turnover_rate") or stock["turnover_rate"] is None):
            stock["turnover_rate"] = tr
            updated = True
        ind = enriched.get("industry", "")
        if ind and (not stock.get("industry") or stock["industry"] == ""):
            stock["industry"] = ind
            updated = True
        return updated

    # ═══════════════════════════════════════════════════
    # API 请求（防反爬）
    # ═══════════════════════════════════════════════════

    def _random_headers(self) -> Dict[str, str]:
        """生成随机化请求头"""
        ua = random.choice(USER_AGENTS)
        ref = random.choice(REFERERS)
        return {
            "User-Agent": ua,
            "Referer": ref,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _fetch_page(
        self, fs: str, page: int, fields: str
    ) -> Tuple[Optional[List[Dict[str, Any]]], float]:
        """
        抓取单页数据，含重试机制。
        返回 (items, elapsed_seconds)
        """
        import httpx
        params = {
            "pn": str(page), "pz": str(PAGE_SIZE),
            "po": "1", "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2", "invt": "2", "fid": "f3",
            "fs": fs, "fields": fields,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            headers = self._random_headers()
            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                    resp = await client.get(EASTMONEY_URL, params=params)
                    elapsed = time.time() - start
                    if resp.status_code != 200:
                        logger.warning(f"东财页{page} HTTP {resp.status_code} (尝试{attempt})")
                        if attempt < MAX_RETRIES:
                            delay = 2 ** attempt + random.uniform(0, 1)
                            await asyncio_create_delay(delay)
                        continue

                    data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", [])
                    if items:
                        return items, elapsed
                    return [], elapsed

            except Exception as e:
                elapsed = time.time() - start
                if attempt < MAX_RETRIES:
                    delay = 2 ** attempt + random.uniform(0, 2)
                    logger.debug(f"东财页{page}失败: {type(e).__name__} (尝试{attempt}), {delay:.1f}s后重试")
                    await asyncio_create_delay(delay)
                else:
                    logger.warning(f"东财页{page}失败({MAX_RETRIES}次): {type(e).__name__}")

        return None, 0

    # ═══════════════════════════════════════════════════
    # 核心富集流程
    # ═══════════════════════════════════════════════════

    async def fetch_and_cache(self):
        """
        从东方财富抓取全市场股票换手率+行业，写入本地缓存。
        可被定时任务调用。
        """
        logger.info("东财富集开始: 抓取全市场数据...")
        fields = "f12,f14,f8,f103"
        # 全市场板块：沪A+科创板 + 深A+创业板 + 北A
        boards = [
            ("m:0+t:6,m:0+t:80", "沪A"),
            ("m:1+t:2,m:1+t:23", "深A"),
            ("m:0+t:81", "北A"),
        ]

        total_fetched = 0
        new_cache = {}  # code -> {turnover_rate, industry}

        for fs, label in boards:
            page = 1
            empty_pages = 0
            while page <= 100:  # 安全上限
                # 随机延迟（防反爬核心手段）
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                await asyncio_create_delay(delay)

                items, elapsed = await self._fetch_page(fs, page, fields)
                if items is None:
                    logger.warning(f"东财富集 [{label}] 第{page}页放弃")
                    break
                if not items:
                    empty_pages += 1
                    if empty_pages >= 3:  # 连续3页空 = 该板块结束
                        break
                    page += 1
                    continue

                empty_pages = 0
                for item in items:
                    code = str(item.get("f12", "")).strip()
                    if not code:
                        continue
                    tr_raw = item.get("f8")
                    ind_raw = item.get("f103", "")
                    turnover_rate = None
                    if tr_raw is not None and str(tr_raw) != "-":
                        try:
                            turnover_rate = float(tr_raw)
                        except (ValueError, TypeError):
                            turnover_rate = None
                    industry = str(ind_raw).strip() if ind_raw and str(ind_raw) != "-" else ""
                    new_cache[code] = {
                        "turnover_rate": turnover_rate,
                        "industry": industry,
                    }
                    total_fetched += 1

                logger.info(
                    f"东财富集 [{label}] 第{page}页: {len(items)}只, "
                    f"耗时{elapsed:.1f}s, 累计{total_fetched}只"
                )
                page += 1

        # 更新缓存
        if new_cache:
            self._cache = new_cache
            self._save_cache()
            logger.info(f"东财富集完成: 共抓取{total_fetched}只")
        else:
            logger.warning("东财富集: 未获取到任何数据，缓存未更新")

        return len(new_cache)

    async def enrich_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """
        将缓存数据应用到股票列表。
        如果缓存过期，先尝试刷新。
        返回更新股票数。
        """
        # 缓存过期？尝试刷新
        if not self.is_cache_fresh():
            logger.info("东财缓存过期，尝试在线刷新...")
            await self.fetch_and_cache()
        elif not self._cache:
            logger.info("东财缓存为空，尝试在线抓取...")
            await self.fetch_and_cache()

        # 应用到股票
        applied = 0
        for stock in stocks:
            if self.apply_to_stock(stock):
                applied += 1

        logger.info(f"东财富集应用: {applied}/{len(stocks)} 只更新")
        return applied


async def asyncio_create_delay(seconds: float):
    """包装 asyncio.sleep，方便调用"""
    import asyncio
    await asyncio.sleep(seconds)


# ═══════════════════════════════════════════════════
# 全局单例
# ═══════════════════════════════════════════════════

_enricher: Optional[EastMoneyEnricher] = None


def get_enricher() -> EastMoneyEnricher:
    global _enricher
    if _enricher is None:
        _enricher = EastMoneyEnricher()
    return _enricher
