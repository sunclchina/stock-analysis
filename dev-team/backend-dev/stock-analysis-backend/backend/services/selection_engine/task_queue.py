"""
异步任务队列（SelectionTaskQueue）。
支持提交选股任务、后台 Worker 执行、前端轮询任务状态。

设计文档 §6.4：
- Submit selection task → 返回 task_id (UUID)
- Worker 线程 (最多3个并发)
- 执行选股并存储结果
- get_result(task_id) 返回状态+结果或进度
- 结果缓存30分钟后自动清理
"""

import uuid
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_CONCURRENT_WORKERS = 3  # i7-6700 4核8线程
RESULT_TTL_SECONDS = 30 * 60  # 30分钟


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class SelectionTask:
    """选股任务"""
    
    def __init__(
        self,
        task_id: str,
        strategy: str,
        params: Dict[str, Any],
        execute_func: Callable,
    ):
        self.task_id = task_id
        self.strategy = strategy
        self.params = params
        self.execute_func = execute_func
        self.status = TaskStatus.PENDING
        self.progress = 0.0  # 0-100
        self.progress_message = ""
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self._cancel_flag = False

    def cancel(self):
        self._cancel_flag = True

    @property
    def is_expired(self) -> bool:
        if self.completed_at is None:
            return False
        return (time.time() - self.completed_at) > RESULT_TTL_SECONDS

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "task_id": self.task_id,
            "strategy": self.strategy,
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
        }
        if self.started_at:
            d["started_at"] = datetime.fromtimestamp(self.started_at).isoformat()
        if self.completed_at:
            d["completed_at"] = datetime.fromtimestamp(self.completed_at).isoformat()
        if self.elapsed:
            d["elapsed_seconds"] = round(self.elapsed, 2)
        if self.status == TaskStatus.COMPLETED and self.result is not None:
            # 结果中只返回概要，完整结果通过 get_result 获取
            d["result_summary"] = {
                "count": len(self.result.get("results", [])),
                "layer_counts": self.result.get("layer_counts", {}),
            }
        if self.error:
            d["error"] = self.error
        return d


class SelectionTaskQueue:
    """
    异步选股任务队列。
    
    线程安全，支持最多 MAX_CONCURRENT_WORKERS 个并发 Worker。
    """
    
    def __init__(self, max_workers: int = MAX_CONCURRENT_WORKERS):
        self._max_workers = max_workers
        self._tasks: Dict[str, SelectionTask] = {}
        self._lock = threading.Lock()
        self._pending: List[str] = []
        self._running: List[str] = []
        self._worker_thread: Optional[threading.Thread] = None
        self._running_flag = True
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # 每秒清理过期结果

    def _start_worker(self):
        """启动后台 Worker 线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running_flag = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="selection-worker"
            )
            self._worker_thread.start()
            logger.info("选任务队列 Worker 已启动")

    def _worker_loop(self):
        """Worker 主循环"""
        while self._running_flag:
            try:
                # 获取待处理任务
                task_id = None
                with self._lock:
                    if self._pending and len(self._running) < self._max_workers:
                        task_id = self._pending.pop(0)
                        self._running.append(task_id)
                
                if task_id:
                    self._execute_task(task_id)
                else:
                    # 清理过期结果
                    self._cleanup_expired()
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker 循环异常: {e}")
                time.sleep(1)

    def _execute_task(self, task_id: str):
        """执行单个任务"""
        task = self._tasks.get(task_id)
        if not task:
            return

        try:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            logger.info(f"执行任务 [{task_id}]: {task.strategy}")

            # 执行选股逻辑
            task.progress = 50.0
            task.progress_message = "正在选股..."
            result = task.execute_func(**task.params)

            task.status = TaskStatus.COMPLETED
            task.progress = 100.0
            task.progress_message = "完成"
            task.result = result
            task.completed_at = time.time()

            count = len(result.get("results", []))
            logger.info(f"任务完成 [{task_id}]: {count} 只, 耗时{task.elapsed:.2f}s")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            logger.error(f"任务失败 [{task_id}]: {e}")
        finally:
            with self._lock:
                if task_id in self._running:
                    self._running.remove(task_id)

    def submit(
        self,
        strategy: str,
        params: Dict[str, Any],
        execute_func: Callable,
    ) -> str:
        """
        提交选股任务。
        
        Args:
            strategy: 策略名称/ID
            params: 执行参数
            execute_func: 执行函数
            
        Returns:
            task_id (UUID字符串)
        """
        task_id = str(uuid.uuid4())
        task = SelectionTask(task_id, strategy, params, execute_func)

        with self._lock:
            self._tasks[task_id] = task
            self._pending.append(task_id)

        self._start_worker()
        logger.info(f"任务已提交 [{task_id}]: {strategy}")
        return task_id

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询任务状态和结果。
        
        Returns:
            {
                "task_id": str,
                "strategy": str,
                "status": "pending"|"running"|"completed"|"failed",
                "progress": float (0-100),
                "progress_message": str,
                "result": {...} | None,  # 仅 completed 时有
                "error": str | None,
                "created_at": str,
                "started_at": str | None,
                "completed_at": str | None,
            }
        """
        with self._lock:
            task = self._tasks.get(task_id)
        
        if not task:
            return None
        
        d = task.to_dict()
        if task.status == TaskStatus.COMPLETED:
            d["result"] = task.result
        
        return d

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.cancel()
                if task_id in self._pending:
                    self._pending.remove(task_id)
                task.status = TaskStatus.FAILED
                task.error = "用户取消"
                task.completed_at = time.time()
                logger.info(f"任务已取消 [{task_id}]")
                return True
        return False

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self._lock:
            return {
                "pending": len(self._pending),
                "running": len(self._running),
                "max_workers": self._max_workers,
                "total_tasks": len(self._tasks),
                "active_workers": len(self._running),
                "available_slots": self._max_workers - len(self._running),
            }

    def _cleanup_expired(self):
        """清理过期结果"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            expired = [
                tid for tid, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                and task.is_expired
                and tid not in self._pending
                and tid not in self._running
            ]
            for tid in expired:
                del self._tasks[tid]
        
        if expired:
            logger.debug(f"清理过期任务: {len(expired)} 个")
        
        self._last_cleanup = now

    def shutdown(self):
        """关闭队列"""
        self._running_flag = False
        logger.info("选股任务队列已关闭")


# 全局单例
selection_task_queue = SelectionTaskQueue()
