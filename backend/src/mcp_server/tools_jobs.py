"""Job-queue tools (enqueue summary/comic, poll status)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastmcp import FastMCP

from src.database.paper_repository import PaperRepository
from src.queue.tasks import (
    enqueue_comic_job,
    enqueue_summary_job,
    get_comic_queue_stats,
    get_job_status,
    get_queue_stats,
)


def register(mcp: FastMCP) -> None:
    repo = PaperRepository()

    @mcp.tool()
    def get_paper_summary(paper_id: str, generate_if_missing: bool = True) -> Dict[str, Any]:
        """Return the AI summary for a paper.

        If missing and `generate_if_missing=True`, enqueue a summary job and
        return the job id so the agent can poll.
        """
        paper = repo.get_paper_by_id(paper_id)
        if not paper:
            return {"error": f"paper {paper_id} not found"}
        if paper.ai_summary:
            return {"paper_id": paper_id, "summary": paper.ai_summary, "status": "ready"}
        if not generate_if_missing:
            return {"paper_id": paper_id, "summary": None, "status": "missing"}
        job_id = enqueue_summary_job(paper_id)
        return {"paper_id": paper_id, "summary": None, "status": "queued", "job_id": job_id}

    @mcp.tool()
    def generate_comic(paper_id: str) -> Dict[str, Any]:
        """Enqueue a comic-generation job for a paper. Returns the RQ job id."""
        if not repo.get_paper_by_id(paper_id):
            return {"error": f"paper {paper_id} not found"}
        job_id = enqueue_comic_job(paper_id)
        return {"paper_id": paper_id, "job_id": job_id, "status": "queued"}

    @mcp.tool()
    def job_status(job_id: str) -> Dict[str, Any]:
        """Poll the status of an RQ job (summary or comic)."""
        status = get_job_status(job_id)
        return {"job_id": job_id, "status": status}

    @mcp.tool()
    def queue_stats() -> Dict[str, Any]:
        """Return queue-depth stats for both summary and comic queues."""
        return {
            "summary": get_queue_stats(),
            "comic": get_comic_queue_stats(),
        }
