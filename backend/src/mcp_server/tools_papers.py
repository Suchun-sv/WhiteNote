"""Paper read / search / triage tools."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from src.crawler.arxiv_client import ArxivClient
from src.database.paper_repository import PaperRepository
from src.database.paper_user_meta_repository import PaperUserMetaRepository
from src.model.paper import Paper

DEFAULT_USER = "mcp"


def _paper_to_dict(paper: Paper, include_full_text: bool = False) -> Dict[str, Any]:
    d = paper.model_dump(mode="json")
    if not include_full_text:
        d.pop("full_text", None)
        d.pop("ai_embedding_doc", None)
    return d


def _short(paper: Paper) -> Dict[str, Any]:
    return {
        "id": paper.id,
        "title": paper.ai_title or paper.title,
        "original_title": paper.title,
        "abstract": paper.ai_abstract or paper.abstract,
        "authors": paper.arxiv_authors or paper.authors,
        "arxiv_entry_id": paper.arxiv_entry_id,
        "arxiv_categories": paper.arxiv_categories,
        "pdf_url": paper.pdf_url,
        "created_at": paper.created_at,
        "favorite_folders": paper.favorite_folders,
        "is_disliked": paper.is_disliked,
        "has_summary": bool(paper.ai_summary),
    }


def register(mcp: FastMCP) -> None:
    repo = PaperRepository()
    meta_repo = PaperUserMetaRepository()

    @mcp.tool()
    def list_recent_papers(limit: int = 20, page: int = 1, include_disliked: bool = False) -> List[Dict[str, Any]]:
        """List the most recently ingested papers (newest first).

        Returns a compact view per paper: id, title, abstract, authors, arxiv id,
        categories, and whether a full AI summary is already cached.
        """
        papers = repo.list_with_filters(
            page=page,
            page_size=limit,
            sort_by="created_at",
            order="desc",
            include_disliked=include_disliked,
            include_favorite=True,
        )
        return [_short(p) for p in papers]

    @mcp.tool()
    def search_papers(query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search already-ingested papers by title substring (case-insensitive)."""
        return [_short(p) for p in repo.search_by_title(query, limit=limit)]

    @mcp.tool()
    def fetch_arxiv_now(keywords: List[str], max_results: int = 20) -> Dict[str, Any]:
        """Crawl arXiv on demand for the given keywords and insert new papers.

        Bypasses the scheduler. Returns counts per keyword and the new paper ids.
        """
        client = ArxivClient()
        results = client.search_papers(keywords=keywords, max_results=max_results)

        flat: List[Paper] = []
        for ps in results.values():
            flat.extend(ps)

        # dedupe within this batch by id
        seen: set[str] = set()
        deduped: List[Paper] = []
        for p in flat:
            if p.id and p.id not in seen:
                seen.add(p.id)
                deduped.append(p)

        inserted = repo.insert_new_papers(deduped)
        return {
            "fetched": {kw: len(ps) for kw, ps in results.items()},
            "inserted_count": len(inserted),
            "inserted_ids": [p.id for p in inserted],
        }

    @mcp.tool()
    def get_paper(paper_id: str, include_full_text: bool = False) -> Optional[Dict[str, Any]]:
        """Get the full record for one paper. `include_full_text=True` pulls the
        extracted PDF text (can be large)."""
        paper = repo.get_paper_by_id(paper_id)
        if not paper:
            return None
        d = _paper_to_dict(paper, include_full_text=include_full_text)
        d["user_meta"] = meta_repo.get_meta(DEFAULT_USER, paper_id)
        return d

    @mcp.tool()
    def mark_paper(paper_id: str, action: str, value: bool = True) -> Dict[str, Any]:
        """Record an agent verdict on a paper.

        `action` is one of: `liked`, `later`, `disliked`, `folder:<name>`.
        - `liked` / `later`: toggles the per-user meta flag (value defaults to True).
        - `disliked`: sets paper.is_disliked (use value=False to clear).
        - `folder:<name>`: adds (value=True) or removes (value=False) the paper from a favorite folder.
        """
        if not repo.get_paper_by_id(paper_id):
            return {"ok": False, "error": f"paper {paper_id} not found"}

        if action == "liked":
            meta_repo.set_like(DEFAULT_USER, paper_id, value)
        elif action == "later":
            meta_repo.set_later(DEFAULT_USER, paper_id, value)
        elif action == "disliked":
            if value:
                repo.mark_disliked(paper_id)
            else:
                repo.unmark_disliked(paper_id)
        elif action.startswith("folder:"):
            folder = action.split(":", 1)[1].strip()
            if not folder:
                return {"ok": False, "error": "folder name is empty"}
            if value:
                repo.add_to_folder(paper_id, folder)
            else:
                repo.remove_from_folder(paper_id, folder)
        else:
            return {"ok": False, "error": f"unknown action: {action}"}

        return {"ok": True, "paper_id": paper_id, "action": action, "value": value}

    @mcp.tool()
    def list_folders() -> Dict[str, int]:
        """List all favorite folders with paper counts."""
        return repo.get_folder_counts()

    @mcp.tool()
    def list_liked_papers(limit: int = 50) -> List[Dict[str, Any]]:
        """List papers the agent (or user) has marked as liked."""
        ids = meta_repo.list_liked(DEFAULT_USER, page=1, page_size=limit)
        out: List[Dict[str, Any]] = []
        for pid in ids:
            p = repo.get_paper_by_id(pid)
            if p:
                out.append(_short(p))
        return out
