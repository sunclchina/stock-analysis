"""
内存缓存工具。
基于 cachetools，提供带TTL的内存缓存。
"""

from cachetools import TTLCache
from typing import Any, Optional


class MemoryCache:
    """
    内存缓存。
    使用 TTLCache 实现，支持过期时间和最大容量。
    """

    def __init__(self, maxsize: int = 1024, ttl: int = 300):
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        self._cache[key] = value

    def delete(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    def contains(self, key: str) -> bool:
        return key in self._cache

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def maxsize(self) -> int:
        return self._cache.maxsize


# 行情缓存（5秒TTL）
quote_cache = MemoryCache(maxsize=1024, ttl=5)

# K线缓存（5分钟TTL）
kline_cache = MemoryCache(maxsize=512, ttl=300)

# 配置缓存（30秒TTL）
config_cache = MemoryCache(maxsize=64, ttl=30)
