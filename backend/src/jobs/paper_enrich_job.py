# src/jobs/paper_enrich_job.py

"""
RQ job: translate paper title and abstract via LLM.

Single job per paper. Skips fields that are already translated.
"""

import logging

from src.config import Config
from src.database.paper_repository import PaperRepository
from src.service.llm_service import init_litellm, translate_title, translate_summary

logger = logging.getLogger(__name__)


def run_paper_enrich_job(paper_id: str) -> dict:
    """
    Translate missing ai_title / ai_abstract for a single paper.

    Returns:
        {"ai_title": bool, "ai_abstract": bool} indicating which fields were set.
    """
    logger.info(f"Starting enrich job for paper: {paper_id}")

    repo = PaperRepository()
    paper = repo.get_paper_by_id(paper_id)

    if not paper:
        logger.error(f"Paper not found: {paper_id}")
        return {"ai_title": False, "ai_abstract": False}

    init_litellm()

    result = {"ai_title": False, "ai_abstract": False}

    # --- Title ---
    if not paper.ai_title:
        try:
            translated = translate_title(paper.title)
            repo.update_ai_title(
                paper_id=paper.id,
                ai_title=translated,
                provider=Config.chat_litellm.model,
            )
            result["ai_title"] = True
            logger.info(f"AI title done: {paper_id}")
        except Exception as e:
            logger.error(f"AI title failed: {paper_id} ({e})")
            raise

    # --- Abstract ---
    if not paper.ai_abstract:
        try:
            translated = translate_summary(paper.abstract)
            repo.update_ai_abstract(
                paper_id=paper.id,
                ai_abstract=translated,
                provider=Config.chat_litellm.model,
            )
            result["ai_abstract"] = True
            logger.info(f"AI abstract done: {paper_id}")
        except Exception as e:
            logger.error(f"AI abstract failed: {paper_id} ({e})")
            raise

    logger.info(f"Enrich job completed: {paper_id} result={result}")
    return result
