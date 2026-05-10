"""Zotero adapter — maps a WhiteNote Paper to a Zotero item and pushes it."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.config import Config
from src.model.paper import Paper


class ZoteroNotConfigured(RuntimeError):
    """Raised when Zotero credentials are missing."""


def _ensure_configured() -> None:
    if not Config.zotero.api_key or not Config.zotero.library_id:
        raise ZoteroNotConfigured(
            "Zotero is not configured. Set ZOTERO__API_KEY and "
            "ZOTERO__LIBRARY_ID in your .env (or zotero.api_key / "
            "zotero.library_id in settings.yaml). Get a key at "
            "https://www.zotero.org/settings/keys."
        )


def _get_client():
    _ensure_configured()
    from pyzotero import zotero  # local import so missing dep is loud

    return zotero.Zotero(
        library_id=Config.zotero.library_id,
        library_type=Config.zotero.library_type,
        api_key=Config.zotero.api_key,
    )


def _split_author(name: str) -> Dict[str, str]:
    """Best-effort split of 'First M. Last' → Zotero creator dict."""
    name = (name or "").strip()
    if not name:
        return {"creatorType": "author", "name": ""}
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return {"creatorType": "author", "firstName": parts[0], "lastName": parts[1]}
    return {"creatorType": "author", "name": name}


def paper_to_zotero_item(paper: Paper, extra_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convert a Paper to a Zotero item payload."""
    is_arxiv = bool(paper.arxiv_entry_id)
    authors = paper.arxiv_authors or paper.authors or []

    tags: List[str] = []
    if paper.arxiv_categories:
        tags.extend(paper.arxiv_categories)
    if extra_tags:
        tags.extend(extra_tags)
    tag_dicts = [{"tag": t} for t in dict.fromkeys(tags) if t]

    abstract = paper.ai_abstract or paper.abstract or ""

    extras: List[str] = []
    if paper.arxiv_entry_id:
        extras.append(f"arXiv: {paper.arxiv_entry_id}")
    if paper.ai_summary:
        # keep extra short; full summary lives in notes (attached separately if desired)
        extras.append(f"WhiteNote AI summary: {paper.ai_summary[:500]}")

    item: Dict[str, Any] = {
        "itemType": "preprint" if is_arxiv else "journalArticle",
        "title": paper.ai_title or paper.title or "",
        "creators": [_split_author(a) for a in authors],
        "abstractNote": abstract,
        "url": paper.pdf_url or "",
        "tags": tag_dicts,
        "extra": "\n".join(extras),
    }

    if paper.arxiv_doi:
        item["DOI"] = paper.arxiv_doi
    if paper.arxiv_published:
        item["date"] = paper.arxiv_published.isoformat() if hasattr(paper.arxiv_published, "isoformat") else str(paper.arxiv_published)
    if is_arxiv:
        item["repository"] = "arXiv"
        item["archiveID"] = paper.arxiv_entry_id

    return item


def list_collections() -> List[Dict[str, str]]:
    """Return [{key, name}, ...] for all top-level collections."""
    zot = _get_client()
    raw = zot.collections()
    return [
        {"key": c["key"], "name": c["data"]["name"]}
        for c in raw
    ]


def save_paper(
    paper: Paper,
    collection_key: Optional[str] = None,
    extra_tags: Optional[List[str]] = None,
    attach_pdf: bool = False,
) -> Dict[str, Any]:
    """Push the paper to Zotero. Returns {item_key, attached_pdf}."""
    zot = _get_client()
    item = paper_to_zotero_item(paper, extra_tags=extra_tags)

    collection = collection_key or Config.zotero.default_collection
    if collection:
        item["collections"] = [collection]

    resp = zot.create_items([item])
    successful = resp.get("successful") or {}
    if not successful:
        raise RuntimeError(f"Zotero rejected the item: {resp}")

    created = next(iter(successful.values()))
    item_key = created["key"]

    attached_pdf = None
    if attach_pdf:
        pdf_path = os.path.join(Config.pdf_save_path, f"{paper.id}.pdf")
        if os.path.exists(pdf_path):
            attach_resp = zot.attachment_simple([pdf_path], item_key)
            attached_pdf = pdf_path if attach_resp else None

    return {"item_key": item_key, "attached_pdf": attached_pdf}
