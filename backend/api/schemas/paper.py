from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from src.model.paper import Paper


# --- Card (list view) ---

class PaperCardResponse(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    ai_title: Optional[str] = None
    ai_abstract: Optional[str] = None
    arxiv_primary_category: Optional[str] = None
    arxiv_categories: Optional[List[str]] = None
    created_at: str
    arxiv_published: Optional[datetime] = None

    @classmethod
    def from_paper(cls, paper: Paper) -> PaperCardResponse:
        return cls(
            id=paper.id,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            ai_title=paper.ai_title,
            ai_abstract=paper.ai_abstract,
            arxiv_primary_category=paper.arxiv_primary_category,
            arxiv_categories=paper.arxiv_categories,
            created_at=paper.created_at,
            arxiv_published=paper.arxiv_published,
        )


# --- Detail (single paper) ---

class PaperDetailResponse(BaseModel):
    id: str
    title: str
    authors: List[str]
    abstract: str
    keywords: List[str]
    pdf_url: Optional[str] = None

    # AI fields
    ai_title: Optional[str] = None
    ai_title_provider: Optional[str] = None
    ai_abstract: Optional[str] = None
    ai_abstract_provider: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_summary_provider: Optional[str] = None

    # Job status
    summary_job_status: Optional[str] = None
    comic_job_status: Optional[str] = None

    # Favorites
    favorite_folders: List[str]
    favorited_at: Optional[str] = None

    # Dislike
    is_disliked: bool = False

    # Timestamps
    created_at: str
    updated_at: str

    # arXiv metadata
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

    @classmethod
    def from_paper(cls, paper: Paper) -> PaperDetailResponse:
        return cls(**paper.model_dump(exclude={"full_text", "ai_embedding_doc"}))


# --- Pagination ---

class PaginationMeta(BaseModel):
    page: int
    size: int
    total: int
    total_pages: int

    @classmethod
    def build(cls, page: int, size: int, total: int) -> PaginationMeta:
        return cls(
            page=page,
            size=size,
            total=total,
            total_pages=max(1, math.ceil(total / size)),
        )


# --- List response ---

class PaperListResponse(BaseModel):
    data: List[PaperCardResponse]
    pagination: PaginationMeta
