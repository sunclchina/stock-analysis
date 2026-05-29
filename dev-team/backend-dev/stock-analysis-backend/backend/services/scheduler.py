"""
定时任务调度器。
使用 BackgroundScheduler（线程池）而非 AsyncIOScheduler。
AsyncIOScheduler 和 uvicorn 共用同一个事件循环，同步阻塞会卡死整个 HTTP 服务。
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio

logger = logging.getLogger(__name__)


class SchedulerManager:
    """定时任务管理器（线程池模式）"""

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._jobs = {}

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("定时任务调度器已启动（线程池模式）")

    def stop(self):
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("定时任务调度器已停止")

    def add_interval_job(self, job_id: str, func, seconds: int, **kwargs):
        """添加间隔任务"""
        if job_id in self._jobs:
            self.remove_job(job_id)

        # 包装 async 函数，在线程池中运行事件循环
        wrapped = self._wrap_async(func) if asyncio.iscoroutinefunction(func) else func

        job = self._scheduler.add_job(
            wrapped,
            IntervalTrigger(seconds=seconds),
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        self._jobs[job_id] = job
        logger.info(f"定时任务 [{job_id}] 已添加，间隔 {seconds} 秒")
        return job

    def add_cron_job(self, job_id: str, func, hour: int, minute: int, **kwargs):
        """添加 cron 定时任务"""
        if job_id in self._jobs:
            self.remove_job(job_id)

        wrapped = self._wrap_async(func) if asyncio.iscoroutinefunction(func) else func

        job = self._scheduler.add_job(
            wrapped,
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        self._jobs[job_id] = job
        logger.info(f"定时任务 [{job_id}] 已添加，每天 {hour:02d}:{minute:02d} 执行")
        return job

    def remove_job(self, job_id: str):
        """移除任务"""
        if job_id in self._jobs:
            self._scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"定时任务 [{job_id}] 已移除")

    def list_jobs(self) -> list:
        """列出所有任务"""
        return [
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    @staticmethod
    def _wrap_async(func):
        """将 async 函数包装为同步函数（在线程中创建新的事件循环运行）"""
        def wrapper(*args, **kwargs):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(func(*args, **kwargs))
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"定时任务 [{func.__name__}] 异常: {e}")
        return wrapper


# 全局单例
scheduler = SchedulerManager()
