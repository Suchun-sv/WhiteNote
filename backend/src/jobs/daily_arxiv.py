# src/jobs/daily_arxiv.py

"""
Daily ArXiv fetch & enrichment job.

This module contains PURE job logic.
It is safe to be called by:
- APScheduler
- CLI
- Future Prefect / Airflow
"""

import asyncio
import re

from tqdm import tqdm

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

from src.database.paper_repository import PaperRepository
from src.config import Config
from src.service.semantic_scholar_service import SemanticScholarClient
from src.jobs.feed_job import run_feed_job



def setup_logging(
    level=logging.INFO,
    log_file: str = "daily_arxiv.log",
):
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---- Console ----
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # ---- File (rotating) ----
    file_handler = RotatingFileHandler(
        LOG_DIR / log_file,
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler],
    )


def run_daily_arxiv_job() -> None:
    """
    Entry point for scheduler.

    NOTE:
    - APScheduler expects a normal sync function
    - Internally we can still use asyncio
    """
    asyncio.run(_run())


async def _run():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Daily ArXiv Job started")

    # --- Init ---
    repo = PaperRepository()

    # --- Fetch papers via feed_job ---
    # Run all feeds that use scheduled crawlers
    for feed_config in Config.feeds:
        if feed_config.schedule:
            try:
                count = run_feed_job(feed_config.id)
                logger.info(f"Feed '{feed_config.id}': {count} new papers inserted")
            except NotImplementedError as e:
                logger.warning(f"Feed '{feed_config.id}' skipped: {e}")
            except Exception as e:
                logger.error(f"Feed '{feed_config.id}' failed: {e}")

    # NOTE: AI title/abstract translation is now handled by the enrich RQ queue.
    # Papers are auto-enqueued for enrichment when inserted via feed_job.py.

    # ---------- Affiliations (Semantic Scholar) ----------
    if Config.semantic_scholar.enabled:
        logger.info("Fetching author affiliations from Semantic Scholar...")

        s2_client = SemanticScholarClient()
        papers = repo.list_missing_affiliations(limit=-1)
        logger.info(f"Total papers to process for affiliations: {len(papers)}")

        for paper in tqdm(papers, desc="Fetching affiliations"):
            try:
                # Extract arXiv ID from arxiv_entry_id or paper.id
                arxiv_id = None
                if paper.arxiv_entry_id:
                    match = re.search(r"(\d{4}\.\d{4,5})", paper.arxiv_entry_id)
                    if match:
                        arxiv_id = match.group(1)
                if not arxiv_id and paper.id and re.match(r"^\d{4}\.\d{4,5}$", paper.id):
                    arxiv_id = paper.id

                if not arxiv_id:
                    logger.debug(f"Skipping paper {paper.id}: no arXiv ID found")
                    # Write empty list so we don't retry
                    repo.update_affiliations(paper.id, [])
                    continue

                affiliations = s2_client.fetch_affiliations(arxiv_id)
                repo.update_affiliations(paper.id, affiliations or [])
            except Exception as e:
                logger.error(f"Affiliation fetch failed: {paper.id} ({e})")

    logger.info("Daily ArXiv job finished")

if __name__ == "__main__":
    run_daily_arxiv_job()
