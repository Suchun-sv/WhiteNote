from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_paper_repo
from api.schemas.paper import (
    PaginationMeta,
    PaperCardResponse,
    PaperDetailResponse,
    PaperListResponse,
)
from api.schemas.collection import FavoriteRequest
from src.database.paper_repository import PaperRepository

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("", response_model=PaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    folder: Optional[str] = Query(default=None),
    repo: PaperRepository = Depends(get_paper_repo),
):
    """List papers with pagination."""
    papers = repo.list_with_filters(
        page=page,
        page_size=size,
        sort_by=sort_by,
        order=order,
        include_disliked=False,
        include_favorite=bool(folder),
        folder_filter=folder,
    )

    total = repo.count_with_filters(
        include_disliked=False,
        folder_filter=folder,
    )

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


# --- Favorite ---

@router.post("/{paper_id}/favorite")
def add_favorite(
    paper_id: str,
    body: FavoriteRequest,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Add a paper to a favorite folder."""
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    added = repo.add_to_folder(paper_id, body.folder)
    return {"success": True, "added": added}


@router.delete("/{paper_id}/favorite")
def remove_favorite(
    paper_id: str,
    folder: str = Query(...),
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Remove a paper from a favorite folder."""
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    removed = repo.remove_from_folder(paper_id, folder)
    return {"success": True, "removed": removed}


# --- Dislike ---

@router.post("/{paper_id}/dislike")
def mark_dislike(
    paper_id: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Mark a paper as disliked."""
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    repo.mark_disliked(paper_id)
    return {"success": True}


@router.delete("/{paper_id}/dislike")
def unmark_dislike(
    paper_id: str,
    repo: PaperRepository = Depends(get_paper_repo),
):
    """Remove dislike mark from a paper."""
    paper = repo.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    repo.unmark_disliked(paper_id)
    return {"success": True}
