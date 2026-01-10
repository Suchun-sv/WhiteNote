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
import arxiv
from tqdm import tqdm

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

from src.crawler.arxiv_client import ArxivClient
from src.database.paper_repository import PaperRepository
from src.service.llm_service import (
    init_litellm,
    translate_summary,
    translate_title,
)
from src.config import Config



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
    logger.info("🌿 LavenderSentinel — Daily ArXiv Job started")

    # --- Init ---
    init_litellm()
    crawler = ArxivClient()
    repo = PaperRepository()

    keywords = Config.keywords

    logger.info("🔎 Fetching new papers from arXiv...")

    keyword_results = crawler.search_papers(
        keywords=keywords,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    total_inserted = 0

    for kw, papers in keyword_results.items():
        inserted = repo.insert_new_papers(papers)
        total_inserted += len(inserted)
        logger.info(f"📌 keyword='{kw}' fetched={len(papers)} inserted={len(inserted)}")

    logger.info(f"📚 Total new papers inserted: {total_inserted}")

    # ---------- AI title ----------
    if Config.auto_ai_title:
        logger.info("🤖 Generating AI titles...")

        papers = repo.list_missing_ai_title(limit=-1)
        logger.info(f"🔍 Total papers to process for AI title: {len(papers)}")

        for paper in tqdm(papers, desc="Generating AI titles"):
            try:
                translated = translate_title(paper.title)
                logger.info(f"🔍 AI title translated: {translated}")
                repo.update_ai_title(
                    paper_id=paper.id,
                    ai_title=translated,
                    provider=Config.chat_litellm.model,
                )
            except Exception as e:
                logger.error(f"❌ AI title failed: {paper.id} ({e})")

    # ---------- AI abstract ----------
    if Config.auto_ai_abstract:
        logger.info("🤖 Generating AI abstracts...")

        papers = repo.list_missing_ai_abstract(limit=-1)
        logger.info(f"🔍 Total papers to process for AI abstract: {len(papers)}")

        for paper in tqdm(papers, desc="Generating AI abstracts"):
            try:
                translated = translate_summary(paper.abstract)
                repo.update_ai_abstract(
                    paper_id=paper.id,
                    ai_abstract=translated,
                    provider=Config.chat_litellm.model,
                )
            except Exception as e:
                logger.error(f"❌ AI abstract failed: {paper.id} ({e})")

    logger.info("🎉 Daily ArXiv job finished")

if __name__ == "__main__":
    run_daily_arxiv_job()