# src/queue/tasks.py

"""
RQ 任务提交封装

提供给 Streamlit UI 调用的接口
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from rq.job import Job, JobStatus
from rq.registry import FinishedJobRegistry, FailedJobRegistry, StartedJobRegistry

from .connection import get_redis_connection, get_summary_queue


def enqueue_summary_job(paper_id: str) -> str:
    """
    提交论文总结任务到队列
    
    Args:
        paper_id: 论文 ID
        
    Returns:
        job_id: RQ 任务 ID，可用于查询状态
    """
    # 延迟导入，避免循环依赖
    from src.jobs.paper_summary_job import run_paper_summary_job
    
    queue = get_summary_queue()
    
    job = queue.enqueue(
        run_paper_summary_job,
        paper_id,
        job_timeout='10h',      # 超时 10 h
        result_ttl=86400,       # 结果保留 24 小时
        failure_ttl=86400 * 7,  # 失败记录保留 7 天
    )
    
    return job.id


def get_job_status(job_id: str) -> Optional[str]:
    """
    查询任务状态
    
    Args:
        job_id: RQ 任务 ID
        
    Returns:
        状态字符串: 'queued' | 'started' | 'finished' | 'failed' | 'canceled' | None
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        status = job.get_status()
        
        # 转换为字符串
        if isinstance(status, JobStatus):
            return status.value
        return str(status)
    except Exception:
        return None


def get_job_result(job_id: str) -> Optional[Any]:
    """
    获取任务执行结果
    
    Args:
        job_id: RQ 任务 ID
        
    Returns:
        任务返回值，如果任务未完成或失败则返回 None
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        return job.result
    except Exception:
        return None


def get_queue_size() -> int:
    """
    获取 summary 队列中等待的任务数
    """
    queue = get_summary_queue()
    return len(queue)


def get_pending_jobs() -> List[Dict[str, Any]]:
    """
    获取队列中所有等待的任务
    
    Returns:
        任务列表，每个任务包含 job_id, paper_id, enqueued_at
    """
    queue = get_summary_queue()
    
    jobs = []
    for job in queue.jobs:
        jobs.append({
            "job_id": job.id,
            "paper_id": job.args[0] if job.args else None,
            "enqueued_at": job.enqueued_at,
            "status": job.get_status(),
        })
    
    return jobs


def cancel_job(job_id: str) -> bool:
    """
    取消一个等待中的任务
    
    Args:
        job_id: RQ 任务 ID
        
    Returns:
        True 如果成功取消，False 如果任务不存在或已开始执行
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        
        # 只能取消等待中的任务
        if job.get_status() == JobStatus.QUEUED:
            job.cancel()
            return True
        return False
    except Exception:
        return False


def retry_failed_job(job_id: str) -> Optional[str]:
    """
    重试一个失败的任务
    
    Args:
        job_id: 失败任务的 ID
        
    Returns:
        新任务的 job_id，如果重试失败则返回 None
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)
        
        if job.get_status() == JobStatus.FAILED:
            # 重新入队
            job.requeue()
            return job.id
        return None
    except Exception:
        return None


def get_queue_stats() -> Dict[str, Any]:
    """
    获取队列的详细统计信息
    
    Returns:
        包含各种统计数据的字典
    """
    queue = get_summary_queue()
    conn = get_redis_connection()
    
    # 各个 registry
    finished_registry = FinishedJobRegistry(queue=queue)
    failed_registry = FailedJobRegistry(queue=queue)
    started_registry = StartedJobRegistry(queue=queue)
    
    # 统计数量
    queued_count = len(queue)
    started_count = len(started_registry)
    finished_count = len(finished_registry)
    failed_count = len(failed_registry)
    
    return {
        "queued": queued_count,
        "started": started_count,
        "finished": finished_count,
        "failed": failed_count,
        "total": queued_count + started_count + finished_count + failed_count,
    }


def get_recent_finished_jobs(hours: int = 24) -> List[Dict[str, Any]]:
    """
    获取最近 N 小时内完成的任务
    
    Args:
        hours: 时间范围（小时）
        
    Returns:
        任务列表
    """
    queue = get_summary_queue()
    conn = get_redis_connection()
    finished_registry = FinishedJobRegistry(queue=queue)
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    jobs = []
    for job_id in finished_registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=conn)
            # 检查完成时间
            if job.ended_at and job.ended_at >= cutoff:
                jobs.append({
                    "job_id": job.id,
                    "paper_id": job.args[0] if job.args else None,
                    "enqueued_at": job.enqueued_at,
                    "started_at": job.started_at,
                    "ended_at": job.ended_at,
                    "status": "finished",
                })
        except Exception:
            continue
    
    # 按完成时间排序（最新在前）
    jobs.sort(key=lambda x: x.get("ended_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return jobs


def get_failed_jobs() -> List[Dict[str, Any]]:
    """
    获取所有失败的任务
    
    Returns:
        失败任务列表
    """
    queue = get_summary_queue()
    conn = get_redis_connection()
    failed_registry = FailedJobRegistry(queue=queue)
    
    jobs = []
    for job_id in failed_registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=conn)
            jobs.append({
                "job_id": job.id,
                "paper_id": job.args[0] if job.args else None,
                "enqueued_at": job.enqueued_at,
                "started_at": job.started_at,
                "ended_at": job.ended_at,
                "exc_info": job.exc_info,
                "status": "failed",
            })
        except Exception:
            continue
    
    # 按失败时间排序（最新在前）
    jobs.sort(key=lambda x: x.get("ended_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return jobs


def get_started_jobs() -> List[Dict[str, Any]]:
    """
    获取正在执行的任务
    
    Returns:
        正在执行的任务列表
    """
    queue = get_summary_queue()
    conn = get_redis_connection()
    started_registry = StartedJobRegistry(queue=queue)
    
    jobs = []
    for job_id in started_registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=conn)
            jobs.append({
                "job_id": job.id,
                "paper_id": job.args[0] if job.args else None,
                "enqueued_at": job.enqueued_at,
                "started_at": job.started_at,
                "status": "started",
            })
        except Exception:
            continue
    
    return jobs

