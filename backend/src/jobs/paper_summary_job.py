# src/jobs/paper_summary_job.py

"""
Paper Summary Job - 单篇论文 AI 总结后台任务

支持：
- APScheduler 一次性任务
- CLI 手动触发
"""

import logging
from pathlib import Path
from typing import Optional

from src.database.paper_repository import PaperRepository
from src.service.llm_service import init_litellm, summarize_long_markdown
from src.service.pdf_parser_service import extract_pdf_markdown
from src.service.pdf_download_service import PdfDownloader
from src.config import Config

logger = logging.getLogger(__name__)


class SummaryJobStatus:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def run_paper_summary_job(paper_id: str) -> None:
    """
    APScheduler 入口：生成单篇论文的 AI 全文总结

    步骤：
    1. 检查 PDF 是否存在，不存在则下载
    2. 解析 PDF 为 Markdown
    3. 调用 LLM 生成总结
    4. 保存到数据库
    """
    logger.info(f"🚀 Starting summary job for paper: {paper_id}")

    repo = PaperRepository()
    paper = repo.get_paper_by_id(paper_id)

    if not paper:
        logger.error(f"❌ Paper not found: {paper_id}")
        return

    try:
        # 更新状态为 running
        repo.update_summary_job_status(paper_id, SummaryJobStatus.RUNNING)

        # --- Step 1: 确保 PDF 存在 ---
        pdf_path = Path(Config.pdf_save_path) / f"{paper_id}.pdf"

        if not pdf_path.exists():
            logger.info(f"📥 Downloading PDF for {paper_id}...")
            downloader = PdfDownloader()
            downloader.download_one(
                f"https://arxiv.org/pdf/{paper_id}.pdf",
                paper_id,
            )

        if not pdf_path.exists():
            raise FileNotFoundError(f"Failed to download PDF: {paper_id}")

        # --- Step 2: 解析 PDF ---
        logger.info(f"📄 Extracting markdown from PDF...")
        with open(pdf_path, "rb") as f:
            md_text = extract_pdf_markdown(f.read())

        # 保存全文
        repo.update_full_text(paper_id, md_text)

        # --- Step 3: 生成 AI 总结 ---
        logger.info(f"🤖 Generating AI summary...")
        init_litellm()

        summary = summarize_long_markdown(
            md_text,
            language=Config.language,
        )

        # --- Step 4: 保存总结 ---
        repo.update_ai_summary(
            paper_id=paper_id,
            ai_summary=summary,
            provider=Config.chat_litellm.model,
        )

        # 更新状态为 completed
        repo.update_summary_job_status(paper_id, SummaryJobStatus.COMPLETED)

        logger.info(f"✅ Summary job completed for paper: {paper_id}")

    except Exception as e:
        logger.error(f"❌ Summary job failed for {paper_id}: {e}")
        repo.update_summary_job_status(paper_id, SummaryJobStatus.FAILED)
        raise


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.jobs.paper_summary_job <paper_id>")
        sys.exit(1)

    paper_id = sys.argv[1]
    run_paper_summary_job(paper_id)

