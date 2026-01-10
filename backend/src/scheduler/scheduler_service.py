# src/scheduler/scheduler_service.py

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from src.config import Config
from src.jobs.daily_arxiv import run_daily_arxiv_job
from src.jobs.paper_summary_job import run_paper_summary_job


class SchedulerService:
    """
    Long-running scheduler service.

    - Starts APScheduler
    - Loads jobs from settings.yaml
    - Supports hot reload (no restart)
    - Summary jobs run in queue mode (one at a time)
    """

    # Executor names
    EXECUTOR_DEFAULT = "default"
    EXECUTOR_SUMMARY_QUEUE = "summary_queue"  # 单线程队列

    def __init__(self):
        # 配置 executors:
        # - default: 默认线程池 (10 workers)
        # - summary_queue: 单线程，确保队列式执行
        executors = {
            self.EXECUTOR_DEFAULT: ThreadPoolExecutor(max_workers=10),
            self.EXECUTOR_SUMMARY_QUEUE: ThreadPoolExecutor(max_workers=1),  # 🔑 队列模式
        }

        self.scheduler = BackgroundScheduler(
            timezone=Config.scheduler.timezone,
            executors=executors,
        )
        self._started = False

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------

    def start(self) -> None:
        """
        Start scheduler (idempotent).
        """
        if self._started:
            return

        if not Config.scheduler.enabled:
            print("⏸ Scheduler disabled by config")
            return

        print("⏱ Starting SchedulerService...")
        self.scheduler.start()
        self.reload()
        self._started = True

    def shutdown(self) -> None:
        """
        Graceful shutdown.
        """
        if not self._started:
            return

        print("🛑 Stopping SchedulerService...")
        self.scheduler.shutdown(wait=False)
        self._started = False

    # --------------------------------------------------
    # Reload logic
    # --------------------------------------------------

    def reload(self) -> None:
        """
        Reload all jobs from config.

        Safe to call multiple times.
        """
        print("🔄 Reloading scheduler jobs...")

        self.scheduler.remove_all_jobs()

        self._add_daily_arxiv(job_id="daily_arxiv", cron_expr=Config.scheduler.daily_arxiv_job)

        self._log_jobs()

    # --------------------------------------------------
    # Job registration
    # --------------------------------------------------

    def _add_daily_arxiv(self, job_id: str, cron_expr: str) -> None:
        """
        Register daily_arxiv job.
        """
        trigger = CronTrigger.from_crontab(cron_expr)

        self.scheduler.add_job(
            run_daily_arxiv_job,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )

        print(f"✅ Job registered: {job_id} ({cron_expr})")

    # --------------------------------------------------
    # One-time jobs (user triggered)
    # --------------------------------------------------

    def add_paper_summary_job(
        self,
        paper_id: str,
        delay_seconds: int = 1,
    ) -> str:
        """
        Submit a one-time job to generate AI summary for a paper.

        🔑 队列机制：
        - 使用 summary_queue executor (max_workers=1)
        - 多个任务会排队，一个完成后再执行下一个
        - 相同 paper_id 的任务不会重复添加

        Args:
            paper_id: The paper ID to generate summary for
            delay_seconds: Delay before running (default 1s)

        Returns:
            job_id: The APScheduler job ID
        """
        job_id = f"paper_summary_{paper_id}"

        # 检查是否已有相同任务在队列中
        existing_job = self.scheduler.get_job(job_id)
        if existing_job:
            print(f"⏳ Job already in queue: {job_id}")
            return job_id

        # 设置延迟触发（立即加入队列）
        run_time = datetime.now() + timedelta(seconds=delay_seconds)
        trigger = DateTrigger(run_date=run_time)

        self.scheduler.add_job(
            run_paper_summary_job,
            trigger=trigger,
            args=[paper_id],
            id=job_id,
            executor=self.EXECUTOR_SUMMARY_QUEUE,  # 🔑 使用单线程队列 executor
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600,  # 1小时内的 misfire 都会执行
        )

        queue_size = self.get_summary_queue_size()
        print(f"📝 Job added to queue: {job_id} (queue size: {queue_size})")
        return job_id

    def get_summary_queue_size(self) -> int:
        """
        Get the number of pending summary jobs in queue.
        """
        jobs = self.scheduler.get_jobs()
        return sum(1 for job in jobs if job.id.startswith("paper_summary_"))

    def get_summary_queue_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all pending summary jobs with their info.

        Returns:
            List of job info dicts with id, paper_id, next_run_time
        """
        jobs = self.scheduler.get_jobs()
        result = []
        for job in jobs:
            if job.id.startswith("paper_summary_"):
                result.append({
                    "job_id": job.id,
                    "paper_id": job.id.replace("paper_summary_", ""),
                    "next_run_time": job.next_run_time,
                })
        return result

    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        Get the status of a job.

        Returns:
            - "scheduled": Job is waiting to run
            - "running": Job is currently executing (approximation)
            - None: Job not found (completed or never existed)
        """
        job = self.scheduler.get_job(job_id)
        if job is None:
            return None
        return "scheduled"

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job.

        Returns:
            True if job was cancelled, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            print(f"❌ Job cancelled: {job_id}")
            return True
        except Exception:
            return False

    # --------------------------------------------------
    # Debug helpers
    # --------------------------------------------------

    def _log_jobs(self) -> None:
        jobs = self.scheduler.get_jobs()
        if not jobs:
            print("⚠️ No scheduled jobs")
            return

        print("📅 Active jobs:")
        for job in jobs:
            print(f"  - {job.id} | next run at {job.next_run_time}")