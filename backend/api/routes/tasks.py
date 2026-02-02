"""
Task monitor API: scheduled jobs, one-off runs, RQ queues, history, logs.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.config import Config
from src.jobs.daily_arxiv import run_daily_arxiv_job
from src.jobs.feed_job import run_feed_job

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# In-memory job run history (last N runs)
_JOB_HISTORY: List[Dict[str, Any]] = []
_HISTORY_MAX = 100
_executor = ThreadPoolExecutor(max_workers=4)
_log_dir = Path("logs")

logger = logging.getLogger(__name__)


def _get_scheduler(request: Request):
    return getattr(request.app.state, "scheduler", None)


def _record_run(
    job_type: str,
    job_id: str,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    status: str = "running",
    result: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    global _JOB_HISTORY
    entry = {
        "job_type": job_type,
        "job_id": job_id,
        "started_at": started_at.isoformat() if started_at else None,
        "ended_at": ended_at.isoformat() if ended_at else None,
        "status": status,
        "result": result,
        "error": error,
    }
    _JOB_HISTORY = ([entry] + _JOB_HISTORY)[:_HISTORY_MAX]


# --- Schemas ---


class ScheduledJob(BaseModel):
    id: str
    next_run_time: Optional[str] = None
    trigger: Optional[str] = None


class QueueStats(BaseModel):
    queued: int
    started: int
    finished: int
    failed: int


class TasksOverview(BaseModel):
    scheduled: List[ScheduledJob]
    summary_queue: QueueStats
    comic_queue: QueueStats
    enrich_queue: QueueStats
    pending_summary_count: int
    pending_comic_count: int
    pending_enrich_count: int


class RunFeedRequest(BaseModel):
    feed_id: str


class RunFeedResponse(BaseModel):
    job_id: str
    message: str


# --- Routes ---


@router.get("/overview", response_model=TasksOverview)
async def get_overview(request: Request) -> TasksOverview:
    """Aggregated stats for sidebar: scheduled jobs, RQ queue counts."""
    scheduled: List[ScheduledJob] = []
    scheduler = _get_scheduler(request)
    if scheduler:
        for job in scheduler.scheduler.get_jobs():
            scheduled.append(
                ScheduledJob(
                    id=job.id,
                    next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
                    trigger=str(job.trigger) if job.trigger else None,
                )
            )

    summary_stats = {"queued": 0, "started": 0, "finished": 0, "failed": 0}
    comic_stats = {"queued": 0, "started": 0, "finished": 0, "failed": 0}
    enrich_stats = {"queued": 0, "started": 0, "finished": 0, "failed": 0}
    try:
        from src.queue import get_queue_stats, get_comic_queue_stats, get_enrich_queue_stats
        summary_stats = get_queue_stats()
        comic_stats = get_comic_queue_stats()
        enrich_stats = get_enrich_queue_stats()
    except Exception as e:
        logger.warning("RQ queues unavailable: %s", e)

    return TasksOverview(
        scheduled=scheduled,
        summary_queue=QueueStats(**summary_stats),
        comic_queue=QueueStats(**comic_stats),
        enrich_queue=QueueStats(**enrich_stats),
        pending_summary_count=summary_stats.get("queued", 0) + summary_stats.get("started", 0),
        pending_comic_count=comic_stats.get("queued", 0) + comic_stats.get("started", 0),
        pending_enrich_count=enrich_stats.get("queued", 0) + enrich_stats.get("started", 0),
    )


@router.get("/scheduled", response_model=List[ScheduledJob])
async def list_scheduled(request: Request) -> List[ScheduledJob]:
    """List all scheduled (cron) jobs."""
    scheduler = _get_scheduler(request)
    if not scheduler:
        return []
    out: List[ScheduledJob] = []
    for job in scheduler.scheduler.get_jobs():
        out.append(
            ScheduledJob(
                id=job.id,
                next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
                trigger=str(job.trigger) if job.trigger else None,
            )
        )
    return out


@router.get("/pending/summary")
async def list_pending_summary() -> List[Dict[str, Any]]:
    """Pending + running jobs in summary queue."""
    try:
        from src.queue import get_pending_jobs, get_started_jobs
        pending = get_pending_jobs()
        started = get_started_jobs()
        for j in pending:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
        for j in started:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
            j["started_at"] = j["started_at"].isoformat() if j.get("started_at") else None
        return started + pending
    except Exception as e:
        logger.warning("RQ summary queue unavailable: %s", e)
        return []


@router.get("/pending/comic")
async def list_pending_comic() -> List[Dict[str, Any]]:
    """Pending + running jobs in comic queue."""
    try:
        from src.queue import get_comic_pending_jobs, get_comic_started_jobs
        pending = get_comic_pending_jobs()
        started = get_comic_started_jobs()
        for j in pending:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
        for j in started:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
            j["started_at"] = j["started_at"].isoformat() if j.get("started_at") else None
        return started + pending
    except Exception as e:
        logger.warning("RQ comic queue unavailable: %s", e)
        return []


@router.get("/pending/enrich")
async def list_pending_enrich() -> List[Dict[str, Any]]:
    """Pending + running jobs in enrich queue."""
    try:
        from src.queue import get_enrich_pending_jobs, get_enrich_started_jobs
        pending = get_enrich_pending_jobs()
        started = get_enrich_started_jobs()
        for j in pending:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
        for j in started:
            j["enqueued_at"] = j["enqueued_at"].isoformat() if j.get("enqueued_at") else None
            j["started_at"] = j["started_at"].isoformat() if j.get("started_at") else None
        return started + pending
    except Exception as e:
        logger.warning("RQ enrich queue unavailable: %s", e)
        return []


@router.get("/enrich-queue/summary")
async def get_enrich_queue_stats_endpoint() -> Dict[str, Any]:
    """Enrich queue stats (queued, started, finished, failed)."""
    try:
        from src.queue import get_enrich_queue_stats
        return get_enrich_queue_stats()
    except Exception as e:
        return {"error": str(e), "queued": 0, "started": 0, "finished": 0, "failed": 0}


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Recent job runs (feed, daily_arxiv, etc.)."""
    return _JOB_HISTORY[:limit]


@router.get("/logs")
async def get_logs(source: str = "daily_arxiv", lines: int = 200) -> Dict[str, Any]:
    """Tail of a log file. source: daily_arxiv | worker | supervisord."""
    allowed = {"daily_arxiv": "daily_arxiv.log", "worker": "rq-worker.log", "supervisord": "supervisord.log"}
    if source not in allowed:
        raise HTTPException(status_code=400, detail=f"Unknown log source. Use one of: {list(allowed.keys())}")
    path = _log_dir / allowed[source]
    if not path.exists():
        return {"source": source, "content": "", "message": "Log file not found"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content_lines = f.readlines()
        content = "".join(content_lines[-lines:])
        return {"source": source, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-feed", response_model=RunFeedResponse)
async def run_feed_now(body: RunFeedRequest, request: Request) -> RunFeedResponse:
    """Trigger a one-off feed crawl (e.g. arXiv, iclr-2026)."""
    feed_id = body.feed_id.strip()
    if not feed_id:
        raise HTTPException(status_code=400, detail="feed_id is required")
    job_id = f"feed_{feed_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    started_at = datetime.now(timezone.utc)
    _record_run("feed", job_id, started_at, status="running")

    def run() -> None:
        try:
            inserted = run_feed_job(feed_id)
            _record_run(
                "feed", job_id, started_at,
                ended_at=datetime.now(timezone.utc),
                status="completed",
                result={"inserted": inserted},
            )
        except Exception as e:
            _record_run(
                "feed", job_id, started_at,
                ended_at=datetime.now(timezone.utc),
                status="failed",
                error=str(e),
            )

    _executor.submit(run)
    return RunFeedResponse(job_id=job_id, message=f"Feed job {feed_id} started.")


@router.post("/run-daily-arxiv")
async def run_daily_arxiv_now(request: Request) -> Dict[str, Any]:
    """Trigger daily ArXiv job once (same as cron)."""
    job_id = f"daily_arxiv_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    started_at = datetime.now(timezone.utc)
    _record_run("daily_arxiv", job_id, started_at, status="running")

    def run() -> None:
        try:
            run_daily_arxiv_job()
            _record_run(
                "daily_arxiv", job_id, started_at,
                ended_at=datetime.now(timezone.utc),
                status="completed",
            )
        except Exception as e:
            _record_run(
                "daily_arxiv", job_id, started_at,
                ended_at=datetime.now(timezone.utc),
                status="failed",
                error=str(e),
            )

    _executor.submit(run)
    return {"job_id": job_id, "message": "Daily ArXiv job started."}


@router.post("/run-enrich-backfill")
async def run_enrich_backfill() -> Dict[str, Any]:
    """Enqueue all papers that are missing ai_title or ai_abstract."""
    from src.database.paper_repository import PaperRepository
    from src.queue import enqueue_enrich_job

    repo = PaperRepository()
    missing_title = repo.list_missing_ai_title(limit=-1)
    missing_abstract = repo.list_missing_ai_abstract(limit=-1)

    # Deduplicate by paper id
    paper_ids = {p.id for p in missing_title} | {p.id for p in missing_abstract}

    enqueued = 0
    for pid in paper_ids:
        try:
            enqueue_enrich_job(pid)
            enqueued += 1
        except Exception as e:
            logger.warning("Failed to enqueue enrich backfill for %s: %s", pid, e)

    return {
        "enqueued": enqueued,
        "total_missing": len(paper_ids),
        "message": f"Enqueued {enqueued} papers for translation.",
    }


@router.get("/summary-queue/summary")
async def get_summary_queue_stats() -> Dict[str, Any]:
    """Summary queue stats (queued, started, finished, failed)."""
    try:
        from src.queue import get_queue_stats
        return get_queue_stats()
    except Exception as e:
        return {"error": str(e), "queued": 0, "started": 0, "finished": 0, "failed": 0}


@router.get("/comic-queue/summary")
async def get_comic_queue_stats() -> Dict[str, Any]:
    """Comic queue stats."""
    try:
        from src.queue import get_comic_queue_stats
        return get_comic_queue_stats()
    except Exception as e:
        return {"error": str(e), "queued": 0, "started": 0, "finished": 0, "failed": 0}
