"""
分批处理工具（BatchProcessor）。
将大量股票按批次处理，批次间自动 sleep，支持进度跟踪。

设计文档 §6.5.2：每批200只，批次间 sleep(0.1s)
"""

import time
import logging
from typing import List, Dict, Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 200
DEFAULT_BATCH_SLEEP = 0.1  # 秒


class BatchProcessor:
    """
    分批处理工具。
    
    用法：
        processor = BatchProcessor(batch_size=200, sleep_seconds=0.1)
        results = processor.process(stocks, my_filter_func)
    """

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE,
                 sleep_seconds: float = DEFAULT_BATCH_SLEEP):
        self.batch_size = batch_size
        self.sleep_seconds = sleep_seconds
        self._total_processed = 0
        self._total_batches = 0
        self._start_time = 0.0

    @property
    def progress(self) -> float:
        """返回处理进度百分比 (0-100)"""
        if self._total == 0:
            return 100.0
        return min(100.0, self._total_processed / self._total * 100)

    @property
    def elapsed(self) -> float:
        """返回已用时间（秒）"""
        if self._start_time == 0:
            return 0.0
        return time.time() - self._start_time

    def process(
        self,
        stocks: List[Dict[str, Any]],
        filter_func: Callable[[Dict[str, Any]], bool],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量过滤股票。
        
        Args:
            stocks: 股票列表
            filter_func: 过滤函数，返回 True 保留
            progress_callback: 进度回调 (processed, total)
            
        Returns:
            过滤后的股票列表
        """
        self._total = len(stocks)
        self._total_processed = 0
        self._total_batches = 0
        self._start_time = time.time()

        result = []
        total = len(stocks)

        for start in range(0, total, self.batch_size):
            batch = stocks[start:start + self.batch_size]
            batch_num = start // self.batch_size + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size

            batch_result = []
            for s in batch:
                try:
                    if filter_func(s):
                        batch_result.append(s)
                except Exception as e:
                    logger.debug(f"分批过滤异常 [{s.get('code', '?')}]: {e}")

            result.extend(batch_result)
            self._total_processed += len(batch)
            self._total_batches = batch_num

            if progress_callback:
                progress_callback(self._total_processed, total)

            # 批次间 sleep（最后一批不需要）
            if start + self.batch_size < total:
                time.sleep(self.sleep_seconds)

        elapsed = time.time() - self._start_time
        logger.debug(
            f"分批处理完成: {total} -> {len(result)}, "
            f"共{self._total_batches}批, 耗时{elapsed:.2f}s"
        )
        return result

    def process_with_enrich(
        self,
        stocks: List[Dict[str, Any]],
        filter_func: Callable[[Dict[str, Any]], bool],
        enrich_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量过滤并富集股票。
        
        Args:
            stocks: 股票列表
            filter_func: 过滤函数
            enrich_func: 富集函数（可选，在过滤前执行）
            progress_callback: 进度回调
            
        Returns:
            过滤+富集后的股票列表
        """
        self._total = len(stocks)
        self._total_processed = 0
        self._total_batches = 0
        self._start_time = time.time()

        result = []
        total = len(stocks)

        for start in range(0, total, self.batch_size):
            batch = stocks[start:start + self.batch_size]

            for s in batch:
                try:
                    # 先富集
                    if enrich_func:
                        s = enrich_func(s)
                    # 再过滤
                    if filter_func(s):
                        result.append(s)
                except Exception as e:
                    logger.debug(f"分批处理异常 [{s.get('code', '?')}]: {e}")

            self._total_processed += len(batch)
            self._total_batches += 1

            if progress_callback:
                progress_callback(self._total_processed, total)

            # 批次间 sleep
            if start + self.batch_size < total:
                time.sleep(self.sleep_seconds)

        return result


def batch_filter(
    stocks: List[Dict[str, Any]],
    filter_func: Callable[[Dict[str, Any]], bool],
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_seconds: float = DEFAULT_BATCH_SLEEP,
) -> List[Dict[str, Any]]:
    """便捷函数：单次批量过滤"""
    processor = BatchProcessor(batch_size, sleep_seconds)
    return processor.process(stocks, filter_func)


def batch_map(
    stocks: List[Dict[str, Any]],
    map_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    batch_size: int = DEFAULT_BATCH_SIZE,
    sleep_seconds: float = DEFAULT_BATCH_SLEEP,
) -> List[Dict[str, Any]]:
    """便捷函数：批量映射（富集）"""
    processor = BatchProcessor(batch_size, sleep_seconds)
    result = []
    total = len(stocks)

    for start in range(0, total, batch_size):
        batch = stocks[start:start + batch_size]
        for s in batch:
            try:
                result.append(map_func(s))
            except Exception as e:
                logger.debug(f"分批映射异常 [{s.get('code', '?')}]: {e}")
        if start + batch_size < total:
            time.sleep(sleep_seconds)

    return result
