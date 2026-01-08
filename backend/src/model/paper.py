from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
import uuid
import arxiv

class Paper(BaseModel):
    """
    Paper 数据模型
    - 适合作为 arXiv -> JSON -> 前端展示 的统一结构
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
 
    title: str
    abstract: str
    authors: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None

    # links: List[HttpUrl] = Field(default_factory=list)
    # pdf_url: Optional[HttpUrl] = None

    # AI 生成字段
    ai_title: Optional[str] = None
    ai_title_provider: Optional[str] = None
    ai_abstract: Optional[str] = None
    ai_abstract_provider: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_embedding_doc: Optional[str] = None
    ai_summary_provider: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    arxiv_entry_id: Optional[str] = None
    arxiv_updated: Optional[datetime] = None
    arxiv_published: Optional[datetime] = None
    arxiv_authors: Optional[List[str]] = None
    arxiv_comment: Optional[str] = None
    arxiv_journal_ref: Optional[str] = None
    arxiv_doi: Optional[str] = None
    arxiv_primary_category: Optional[str] = None
    arxiv_categories: Optional[List[str]] = None
    arxiv_links: Optional[List[str]] = None

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "extra": "ignore", 
    }