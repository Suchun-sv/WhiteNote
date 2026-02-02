"""
Unified feed job — runs a crawler for a given feed and inserts papers.

Usage:
    from src.jobs.feed_job import run_feed_job
    run_feed_job("arxiv")        # run arXiv crawler
    run_feed_job("iclr-2026")    # run OpenReview crawler
"""

import logging

from src.config import Config
from src.crawler.registry import CRAWLER_REGISTRY
from src.database.paper_repository import PaperRepository

logger = logging.getLogger(__name__)


def run_feed_job(feed_id: str) -> int:
    """
    Run the crawler for a specific feed and insert new papers.

    Returns the number of newly inserted papers.
    """
    # Find the feed config
    feed_config = None
    for f in Config.feeds:
        if f.id == feed_id:
            feed_config = f
            break

    if not feed_config:
        raise ValueError(f"Feed '{feed_id}' not found in settings.yaml")

    crawler_type = feed_config.crawler
    if crawler_type not in CRAWLER_REGISTRY:
        raise ValueError(
            f"Crawler type '{crawler_type}' not registered. "
            f"Available: {list(CRAWLER_REGISTRY.keys())}"
        )

    # Instantiate crawler with feed-specific params
    crawler_cls = CRAWLER_REGISTRY[crawler_type]
    params = dict(feed_config.params or {})
    if crawler_type == "dblp" and Config.semantic_scholar.enabled:
        params.setdefault("s2_api_key", Config.semantic_scholar.api_key)
        params.setdefault("s2_min_interval", Config.semantic_scholar.min_interval)
    crawler = crawler_cls(params)

    logger.info(f"Running crawler '{crawler_type}' for feed '{feed_id}'...")

    # Fetch papers
    papers = crawler.fetch()

    # Tag each paper with the feed ID
    for p in papers:
        p.feed = feed_id

    # Insert into database
    repo = PaperRepository()
    inserted = repo.insert_new_papers(papers)

    logger.info(
        f"Feed '{feed_id}': fetched={len(papers)} inserted={len(inserted)}"
    )

    # Auto-enqueue enrichment (title/abstract translation)
    if inserted and (Config.auto_ai_title or Config.auto_ai_abstract):
        from src.queue.tasks import enqueue_enrich_job

        enqueued = 0
        for paper in inserted:
            try:
                enqueue_enrich_job(paper.id)
                enqueued += 1
            except Exception as e:
                logger.warning(f"Failed to enqueue enrich for {paper.id}: {e}")
        logger.info(f"Feed '{feed_id}': enqueued {enqueued} enrich jobs")

    return len(inserted)
