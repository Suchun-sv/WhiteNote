# src/queue/__init__.py

"""
RQ (Redis Queue) 任务队列模块

提供：
- Redis 连接管理
- 队列定义
- 任务提交封装
"""

from .connection import get_redis_connection, get_queue, QUEUE_SUMMARY, QUEUE_DEFAULT
from .tasks import (
    enqueue_summary_job,
    get_job_status,
    get_queue_size,
    get_pending_jobs,
    get_queue_stats,
    get_recent_finished_jobs,
    get_failed_jobs,
    get_started_jobs,
    cancel_job,
    retry_failed_job,
)

__all__ = [
    # 连接
    "get_redis_connection",
    "get_queue",
    "QUEUE_SUMMARY",
    "QUEUE_DEFAULT",
    # 任务
    "enqueue_summary_job",
    "get_job_status",
    "get_queue_size",
    "get_pending_jobs",
    "get_queue_stats",
    "get_recent_finished_jobs",
    "get_failed_jobs",
    "get_started_jobs",
    "cancel_job",
    "retry_failed_job",
]

