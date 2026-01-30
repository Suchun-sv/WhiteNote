from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_paper_repo
from api.schemas.paper import (
    PaginationMeta,
    PaperCardResponse,
    PaperDetailResponse,
    PaperListResponse,
)
from src.database.paper_repository import PaperRepository

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("", response_model=PaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    repo: PaperRepository = Depends(get_paper_repo),
):
    """List papers with pagination."""
    papers = repo.list_with_filters(
        page=page,
        page_size=size,
        sort_by=sort_by,
        order=order,
        include_disliked=False,
        include_favorite=False,
    )

    total = repo.count_with_filters(include_disliked=False)

    # Application-level keyword filter (M1 limitation)
    if keyword:
        kw = keyword.lower()
        papers = [
            p
            for p in papers
            if kw in p.title.lower()
            or (p.ai_title and kw in p.ai_title.lower())
            or (p.arxiv_primary_category and kw in p.arxiv_primary_category.lower())
            or any(kw in cat.lower() for cat in (p.arxiv_categories or []))
        ]

    cards = [PaperCardResponse.from_paper(p) for p in papers]
    pagination = PaginationMeta.build(page=page, size=size, total=total)

    return PaperListResponse(data=cards, pagination=pagination)


@router.get("/{paper_id}", response_model=PaperDetailResponse)
def get_paper(
    paper_id: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Get a single paper by ID."""
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperDetailResponse.from_paper(paper)
