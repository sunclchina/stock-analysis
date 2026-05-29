"""
K线数据持久缓存。
当交易日K线API可用时自动缓存，周末/节假日API不可用时回读缓存。
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "data" / "kline_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_HOURS = 168  # 7天


def _cache_path(code: str) -> Path:
    return CACHE_DIR / f"{code}.json"


def kline_cache_save(code: str, klines: List[Dict[str, Any]]) -> None:
    """保存K线数据到磁盘缓存"""
    if not klines:
        return
    try:
        data = {
            "code": code,
            "cached_at": datetime.now().isoformat(),
            "count": len(klines),
            "klines": klines,
        }
        with open(_cache_path(code), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except Exception as e:
        logger.debug(f"K线缓存写入失败 ({code}): {e}")


def kline_cache_load(code: str) -> Optional[List[Dict[str, Any]]]:
    """从磁盘缓存读取K线数据（缓存7天内有效）"""
    path = _cache_path(code)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 检查缓存是否过期
        cached_at = data.get("cached_at", "")
        if cached_at:
            try:
                ct = datetime.fromisoformat(cached_at)
                if datetime.now() - ct > timedelta(hours=CACHE_TTL_HOURS):
                    logger.debug(f"K线缓存过期 ({code}): {cached_at}")
                    return None
            except ValueError:
                return None
        return data.get("klines", [])
    except Exception as e:
        logger.debug(f"K线缓存读取失败 ({code}): {e}")
        return None


def kline_cache_clear_old() -> int:
    """清理过期缓存文件，返回清理数量"""
    count = 0
    now = datetime.now()
    for f in CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            cached_at = data.get("cached_at", "")
            if cached_at:
                ct = datetime.fromisoformat(cached_at)
                if now - ct > timedelta(hours=CACHE_TTL_HOURS):
                    f.unlink()
                    count += 1
        except Exception:
            f.unlink()
            count += 1
    return count
