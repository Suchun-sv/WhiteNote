# src/jobs/paper_comic_job.py

"""
Paper Comic Job - 论文漫画图生成后台任务

支持：
- RQ 后台队列
- CLI 手动触发
"""

import logging
from typing import Optional

from src.database.paper_repository import PaperRepository
from src.service.image_generation_service import generate_paper_comic, comic_exists
from src.config import Config

logger = logging.getLogger(__name__)


class ComicJobStatus:
    """任务状态常量"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def run_paper_comic_job(paper_id: str) -> Optional[str]:
    """
    RQ 入口：生成单篇论文的漫画解读图
    
    步骤：
    1. 获取论文信息
    2. 使用 AI 摘要或全文总结作为内容
    3. 调用 Gemini 生成漫画
    4. 返回生成的图片路径
    
    Returns:
        生成的图片路径，失败返回 None
    """
    logger.info(f"🎨 Starting comic job for paper: {paper_id}")
    
    repo = PaperRepository()
    paper = repo.get_paper_by_id(paper_id)
    
    if not paper:
        logger.error(f"❌ Paper not found: {paper_id}")
        return None
    
    try:
        # 更新状态为 running
        repo.update_comic_job_status(paper_id, ComicJobStatus.RUNNING)
        
        # 检查是否已存在
        if comic_exists(paper_id):
            logger.info(f"📄 Comic already exists for: {paper_id}")
            repo.update_comic_job_status(paper_id, ComicJobStatus.COMPLETED)
            return str(generate_paper_comic(paper_id, "", force=False))
        
        # 获取论文内容：优先使用 full_text，其次 AI 总结，最后摘要
        content = paper.full_text or paper.ai_summary or paper.ai_abstract or paper.abstract
        if not content:
            logger.error(f"❌ No content available for paper: {paper_id}")
            repo.update_comic_job_status(paper_id, ComicJobStatus.FAILED)
            return None
        
        logger.info(f"📝 Using content source: {'full_text' if paper.full_text else 'ai_summary' if paper.ai_summary else 'abstract'}")
        
        # 添加标题信息
        full_content = f"# {paper.title}\n\n{content}"
        
        # 生成漫画
        logger.info(f"🎨 Generating comic for: {paper.title[:50]}...")
        result = generate_paper_comic(
            paper_id=paper_id,
            paper_content=full_content,
            force=False,
        )
        
        if result:
            logger.info(f"✅ Comic generated: {result}")
            repo.update_comic_job_status(paper_id, ComicJobStatus.COMPLETED)
            return str(result)
        else:
            logger.error(f"❌ Comic generation returned None for: {paper_id}")
            repo.update_comic_job_status(paper_id, ComicJobStatus.FAILED)
            return None
            
    except Exception as e:
        logger.error(f"❌ Comic job failed for {paper_id}: {e}")
        repo.update_comic_job_status(paper_id, ComicJobStatus.FAILED)
        raise


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.jobs.paper_comic_job <paper_id>")
        sys.exit(1)
    
    paper_id = sys.argv[1]
    result = run_paper_comic_job(paper_id)
    if result:
        print(f"✅ Comic saved to: {result}")
    else:
        print("❌ Failed to generate comic")
        sys.exit(1)

